"""Build the left/right PCB appearance from the repository EasyEDA JSON files.

The generated PCB assemblies intentionally stay separate from the cases and
switches so the assembly-level Exploded View can move them as their own layer.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "3d-preview/Surround1x0-AKDK.blend"
PCB_DIR = ROOT / "pcb"
COLLECTION_NAME = "02c_PCB"
REVISION = "repository-easyeda-pcb-v3-all-through-holes"

EASYEDA_TO_MM = 0.254
PCB_X_OFFSET_MM = -108.75
PCB_Y_OFFSET_MM = 91.8
BOARD_CENTER_Z = -1.85
BOARD_THICKNESS = 1.6
BOARD_TOP_Z = BOARD_CENTER_Z + BOARD_THICKNESS / 2
BOARD_BOTTOM_Z = BOARD_CENTER_Z - BOARD_THICKNESS / 2


def pcb_xy(x: float, y: float) -> tuple[float, float]:
    return x * EASYEDA_TO_MM + PCB_X_OFFSET_MM, PCB_Y_OFFSET_MM - y * EASYEDA_TO_MM


def ensure_collection(name: str, parent: bpy.types.Collection) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    if collection.name not in parent.children:
        parent.children.link(collection)
    return collection


def clean_generated(collection: bpy.types.Collection) -> None:
    for obj in list(collection.all_objects):
        if obj.get("pcb_generated") is True or obj.name.startswith(("Left_PCB", "Right_PCB")):
            bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.curves):
        for datablock in list(datablocks):
            if datablock.users == 0 and datablock.name.startswith(("Left_PCB", "Right_PCB")):
                datablocks.remove(datablock)


def ensure_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.45,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if not material.use_nodes:
        material.use_nodes = True
    material.diffuse_color = color
    bsdf = next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    material["pcb_generated"] = True
    return material


def mark_generated(obj: bpy.types.Object, side: str, role: str) -> bpy.types.Object:
    obj["pcb_generated"] = True
    obj["pcb_source"] = f"pcb/Surround1x0-AKDK-{side.lower()}-pcb.json"
    obj["pcb_side"] = side
    obj["pcb_role"] = role
    obj["pcb_revision"] = REVISION
    return obj


def parse_track(record: str) -> tuple[float, int, list[tuple[float, float]]] | None:
    parts = record.split("~")
    if len(parts) < 5 or parts[0] != "TRACK":
        return None
    try:
        width = float(parts[1]) * EASYEDA_TO_MM
        layer = int(parts[2])
        values = [float(value) for value in parts[4].split()]
    except (ValueError, IndexError):
        return None
    points = [pcb_xy(values[index], values[index + 1]) for index in range(0, len(values) - 1, 2)]
    return width, layer, points


def board_outline(data: dict) -> list[tuple[float, float]]:
    candidates = []
    for shape in data["shape"]:
        parsed = parse_track(shape)
        if parsed is not None and parsed[1] == 10:
            candidates.append(parsed[2])
    if not candidates:
        raise RuntimeError("EasyEDA BoardOutLine track was not found")
    points = max(candidates, key=len)
    if Vector(points[0]).to_2d() == Vector(points[-1]).to_2d():
        points = points[:-1]
    return points


def create_board_mesh(
    name: str,
    outline: list[tuple[float, float]],
    collection: bpy.types.Collection,
    mask_material: bpy.types.Material,
    edge_material: bpy.types.Material,
) -> bpy.types.Object:
    count = len(outline)
    vertices = [(x, y, BOARD_TOP_Z) for x, y in outline]
    vertices.extend((x, y, BOARD_BOTTOM_Z) for x, y in outline)
    faces = [tuple(range(count)), tuple(range(count, count * 2))[::-1]]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mask_material)
    mesh.materials.append(edge_material)
    for polygon in mesh.polygons[2:]:
        polygon.material_index = 1
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def add_ribbon(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, int, int, int]],
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    z: float,
) -> None:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    base = len(vertices)
    vertices.extend(
        [
            (start[0] + nx, start[1] + ny, z),
            (end[0] + nx, end[1] + ny, z),
            (end[0] - nx, end[1] - ny, z),
            (start[0] - nx, start[1] - ny, z),
        ]
    )
    faces.append((base, base + 1, base + 2, base + 3))


def create_tracks(
    name: str,
    data: dict,
    layer: int,
    z: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for record in data["shape"]:
        parsed = parse_track(record)
        if parsed is None or parsed[1] != layer:
            continue
        width, _record_layer, points = parsed
        for start, end in zip(points, points[1:]):
            add_ribbon(vertices, faces, start, end, max(width, 0.10), z)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def rotated_rect(
    center: tuple[float, float], width: float, height: float, rotation_degrees: float
) -> list[tuple[float, float]]:
    angle = math.radians(-rotation_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    points = []
    for x, y in ((-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2)):
        points.append((center[0] + x * cosine - y * sine, center[1] + x * sine + y * cosine))
    return points


def add_flat_shape(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float],
    width: float,
    height: float,
    rotation: float,
    z: float,
    circular: bool = False,
) -> None:
    if circular:
        points = []
        segments = 12
        for index in range(segments):
            angle = math.tau * index / segments
            points.append((center[0] + math.cos(angle) * width / 2, center[1] + math.sin(angle) * height / 2))
    else:
        points = rotated_rect(center, width, height, rotation)
    base = len(vertices)
    vertices.extend((x, y, z) for x, y in points)
    faces.append(tuple(range(base, base + len(points))))


def library_records(data: dict) -> list[tuple[list[str], list[list[str]]]]:
    result = []
    for shape in data["shape"]:
        if not shape.startswith("LIB~"):
            continue
        chunks = shape.split("#@$")
        header = chunks[0].split("~")
        records = [chunk.split("~") for chunk in chunks[1:]]
        result.append((header, records))
    return result


def collect_drill_holes(data: dict) -> list[tuple[tuple[float, float], float]]:
    holes = []
    for _header, records in library_records(data):
        for parts in records:
            try:
                if parts[0] == "HOLE" and len(parts) > 3:
                    center = pcb_xy(float(parts[1]), float(parts[2]))
                    # EasyEDA's HOLE field stores the radius in 10 mil units.
                    diameter = float(parts[3]) * EASYEDA_TO_MM * 2.0
                elif (
                    parts[0] == "PAD"
                    and len(parts) > 9
                    and parts[6] == "11"
                    and parts[9]
                    and float(parts[9]) > 0
                ):
                    center = pcb_xy(float(parts[2]), float(parts[3]))
                    # Multi-layer PAD drill is also stored as a radius. This
                    # includes the Auto-KDK conthrough and connector bores.
                    diameter = float(parts[9]) * EASYEDA_TO_MM * 2.0
                else:
                    continue
            except (ValueError, IndexError):
                continue
            holes.append((center, diameter))
    # Some library footprints repeat the same mechanical hole in pad and HOLE
    # records. Keep the largest reference diameter for each physical bore.
    deduplicated: dict[tuple[float, float], tuple[tuple[float, float], float]] = {}
    for center, diameter in holes:
        key = (round(center[0], 4), round(center[1], 4))
        previous = deduplicated.get(key)
        if previous is None or diameter > previous[1]:
            deduplicated[key] = (center, diameter)
    return list(deduplicated.values())


def add_cylinder_cutter(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float],
    diameter: float,
    segments: int = 16,
) -> None:
    bottom = BOARD_BOTTOM_Z - 0.8
    top = BOARD_TOP_Z + 0.8
    radius = diameter / 2
    base = len(vertices)
    for z in (bottom, top):
        for index in range(segments):
            angle = math.tau * index / segments
            vertices.append(
                (
                    center[0] + math.cos(angle) * radius,
                    center[1] + math.sin(angle) * radius,
                    z,
                )
            )
    faces.append(tuple(base + index for index in reversed(range(segments))))
    faces.append(tuple(base + segments + index for index in range(segments)))
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append(
            (
                base + index,
                base + next_index,
                base + segments + next_index,
                base + segments + index,
            )
        )


def cut_drill_holes(
    board: bpy.types.Object,
    holes: list[tuple[tuple[float, float], float]],
    collection: bpy.types.Collection,
) -> None:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for center, diameter in holes:
        add_cylinder_cutter(vertices, faces, center, diameter)

    mesh = bpy.data.meshes.new(f"{board.name}_Hole_Cutters_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cutter = bpy.data.objects.new(f"{board.name}_Hole_Cutters", mesh)
    collection.objects.link(cutter)

    modifier = board.modifiers.new("PCB_Actual_Drill_Holes", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter

    bpy.ops.object.select_all(action="DESELECT")
    board.select_set(True)
    bpy.context.view_layer.objects.active = board
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def create_pads(
    side: str,
    data: dict,
    collection: bpy.types.Collection,
    pad_material: bpy.types.Material,
) -> bpy.types.Object:
    pad_vertices: list[tuple[float, float, float]] = []
    pad_faces: list[tuple[int, ...]] = []
    for _header, records in library_records(data):
        for parts in records:
            if parts[0] == "PAD" and len(parts) > 6:
                try:
                    center = pcb_xy(float(parts[2]), float(parts[3]))
                    width = float(parts[4]) * EASYEDA_TO_MM
                    height = float(parts[5]) * EASYEDA_TO_MM
                    layer = int(parts[6])
                    rotation = float(parts[11]) if len(parts) > 11 and parts[11] else 0.0
                except (ValueError, IndexError):
                    continue
                if layer not in {1, 2, 11}:
                    continue
                z = BOARD_TOP_Z + 0.025 if layer in {1, 11} else BOARD_BOTTOM_Z - 0.025
                add_flat_shape(
                    pad_vertices,
                    pad_faces,
                    center,
                    width,
                    height,
                    rotation,
                    z,
                    circular=parts[1] in {"ELLIPSE", "OVAL"},
                )
                if layer == 11:
                    add_flat_shape(
                        pad_vertices,
                        pad_faces,
                        center,
                        width,
                        height,
                        rotation,
                        BOARD_BOTTOM_Z - 0.025,
                        circular=parts[1] in {"ELLIPSE", "OVAL"},
                    )
    name = f"{side}_PCB_Exposed_Pads"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(pad_vertices, [], pad_faces)
    mesh.materials.append(pad_material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def create_silkscreen_text(
    side: str,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{side}_PCB_Silkscreen_Text_Curve", "FONT")
    curve.body = f"SURROUND1x0  {side.upper()}"
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 2.5
    curve.extrude = 0.018
    curve.resolution_u = 2
    obj = bpy.data.objects.new(f"{side}_PCB_Silkscreen", curve)
    collection.objects.link(obj)
    obj.location = (-20.0, 50.0, BOARD_TOP_Z + 0.035)
    curve.materials.append(material)
    return obj


def setup_exploded_view(enabled: bool, spacing: float) -> dict:
    module_path = Path(__file__).with_name("setup_assembly_exploded_view.py")
    spec = importlib.util.spec_from_file_location("akdk_exploded_setup", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.setup_exploded_view(enabled=enabled, spacing_mm=spacing)


def build_hotswap_sockets() -> dict:
    module_path = Path(__file__).with_name("build_choc_hotswap_sockets.py")
    spec = importlib.util.spec_from_file_location("akdk_socket_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_sockets(save=False, setup_exploded=False)


def build_controller_sensor_modules() -> dict:
    module_path = Path(__file__).with_name("build_controller_sensor_modules.py")
    spec = importlib.util.spec_from_file_location("akdk_controller_sensor_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_modules(save=False, setup_exploded=False)


def build() -> dict:
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    keyboard_collection = bpy.data.collections.get("Keyboard_Model")
    keyboard_root = bpy.data.objects.get("Keyboard_Root")
    if keyboard_collection is None or keyboard_root is None:
        raise RuntimeError("Keyboard_Model or Keyboard_Root is missing")

    collection = ensure_collection(COLLECTION_NAME, keyboard_collection)
    clean_generated(collection)

    materials = {
        "mask": ensure_material("PCB_SolderMask_Black", (0.012, 0.028, 0.024, 1), roughness=0.28),
        "edge": ensure_material("PCB_FR4_Edge", (0.38, 0.28, 0.13, 1), roughness=0.72),
        "trace_top": ensure_material("PCB_Trace_Top", (0.22, 0.18, 0.07, 1), roughness=0.34, metallic=0.35),
        "trace_bottom": ensure_material("PCB_Trace_Bottom", (0.12, 0.10, 0.045, 1), roughness=0.38, metallic=0.28),
        "pad": ensure_material("PCB_Exposed_Copper", (0.68, 0.38, 0.08, 1), roughness=0.23, metallic=0.72),
        "silk": ensure_material("PCB_Silkscreen_White", (0.76, 0.80, 0.77, 1), roughness=0.64),
    }

    generated_count = 0
    pcb_summaries = {}
    for side in ("Left", "Right"):
        data_path = PCB_DIR / f"Surround1x0-AKDK-{side.lower()}-pcb.json"
        data = json.loads(data_path.read_text())
        half_root = bpy.data.objects.get(f"{side}_Half_Root")
        if half_root is None:
            raise RuntimeError(f"Missing {side}_Half_Root")

        assembly = bpy.data.objects.new(f"{side}_PCB_Assembly", None)
        collection.objects.link(assembly)
        assembly.parent = half_root
        assembly.matrix_parent_inverse = Matrix.Identity(4)
        assembly.matrix_basis = Matrix.Identity(4)
        assembly["pcb_assembly"] = True
        mark_generated(assembly, side, "assembly")

        outline = board_outline(data)
        drill_holes = collect_drill_holes(data)
        board = create_board_mesh(
            f"{side}_PCB_Substrate",
            outline,
            collection,
            materials["mask"],
            materials["edge"],
        )
        cut_drill_holes(board, drill_holes, collection)
        objects = [
            board,
            create_tracks(f"{side}_PCB_Top_Traces", data, 1, BOARD_TOP_Z + 0.012, collection, materials["trace_top"]),
            create_tracks(f"{side}_PCB_Bottom_Traces", data, 2, BOARD_BOTTOM_Z - 0.012, collection, materials["trace_bottom"]),
            create_pads(side, data, collection, materials["pad"]),
        ]
        objects.append(create_silkscreen_text(side, collection, materials["silk"]))

        for obj in objects:
            obj.parent = assembly
            obj.matrix_parent_inverse = Matrix.Identity(4)
            mark_generated(obj, side, obj.name.removeprefix(f"{side}_PCB_"))
        generated_count += len(objects) + 1
        pcb_summaries[side] = {
            "source": str(data_path.relative_to(ROOT)),
            "outline_points": len(outline),
            "drill_holes": len(drill_holes),
            "generated_objects": len(objects) + 1,
            "source_shapes": len(data["shape"]),
        }

    socket_summary = build_hotswap_sockets()
    controller_sensor_summary = build_controller_sensor_modules()
    enabled = bool(keyboard_root.get("exploded_view_enabled", True))
    spacing = float(keyboard_root.get("exploded_view_spacing_mm", 30.0))
    exploded_summary = setup_exploded_view(enabled=enabled, spacing=spacing)
    keyboard_root["pcb_model_source"] = "pcb/Surround1x0-AKDK-{left,right}-pcb.json"
    keyboard_root["pcb_model_revision"] = REVISION
    keyboard_root["pcb_model_object_count"] = generated_count
    keyboard_root["pcb_board_thickness_mm"] = BOARD_THICKNESS

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    return {
        "revision": REVISION,
        "blend": str(BLEND_PATH),
        "generated_objects": generated_count,
        "pcbs": pcb_summaries,
        "sockets": socket_summary,
        "controller_sensor": controller_sensor_summary,
        "exploded_view": exploded_summary,
    }


if __name__ == "__main__":
    print("PCB_BUILD_RESULT=" + json.dumps(build(), ensure_ascii=False, sort_keys=True))
