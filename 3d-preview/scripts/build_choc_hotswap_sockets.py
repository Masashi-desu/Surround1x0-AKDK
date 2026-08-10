"""Build Kailh CPG135001S30 hot-swap sockets from the supplied datasheet.

The sockets remain separate from the PCB substrate and are grouped as their
own assembly-level Exploded View layer.  Their two locating bosses are aligned
to the EasyEDA CPG135001S30 footprint holes rather than inferred from the
rendered switch positions.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "3d-preview/Surround1x0-AKDK.blend"
PCB_DIR = ROOT / "pcb"
COLLECTION_NAME = "02d_Switch_Sockets"
REVISION = "kailh-cpg135001s30-datasheet-v1"
DATASHEET_RELATIVE_PATH = (
    ".tmp/keyboard-model/reference/socket/"
    "CPG135001S30 hot swap socket for Choc Switch.pdf"
)

EASYEDA_TO_MM = 0.254
PCB_X_OFFSET_MM = -108.75
PCB_Y_OFFSET_MM = 91.8
BOARD_CENTER_Z = -1.85
BOARD_THICKNESS = 1.60
BOARD_BOTTOM_Z = BOARD_CENTER_Z - BOARD_THICKNESS / 2

# CPG135001S30 drawing dimensions, millimetres.
BODY_LENGTH = 9.55
BODY_WIDTH = 6.85
TERMINAL_OVERALL_LENGTH = 13.15
BODY_HEIGHT = 1.80
OVERALL_HEIGHT = 3.05
BOSS_HEIGHT = OVERALL_HEIGHT - BODY_HEIGHT
BOSS_OUTER_DIAMETER = 2.90
BOSS_INNER_DIAMETER = 1.20
PCB_RECOMMENDED_HOLE_DIAMETER = 3.00
CONTACT_OFFSET_X = 5.00
CONTACT_OFFSET_Y = -2.20
SOCKET_TOP_CLEARANCE = 0.05

LOCAL_CONTACT_A = (-CONTACT_OFFSET_X / 2, -CONTACT_OFFSET_Y / 2)
LOCAL_CONTACT_B = (CONTACT_OFFSET_X / 2, CONTACT_OFFSET_Y / 2)


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
        if obj.get("socket_generated") is True or obj.name.startswith(
            ("Left_Socket_", "Right_Socket_", "Left_Sockets_", "Right_Sockets_")
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0 and mesh.name.startswith("CPG135001S30_"):
            bpy.data.meshes.remove(mesh)


def ensure_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
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
    material["socket_generated"] = True
    return material


def add_prism(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    outline: list[tuple[float, float]],
    z_min: float,
    z_max: float,
) -> None:
    base = len(vertices)
    count = len(outline)
    vertices.extend((x, y, z_min) for x, y in outline)
    vertices.extend((x, y, z_max) for x, y in outline)
    faces.append(tuple(base + index for index in reversed(range(count))))
    faces.append(tuple(base + count + index for index in range(count)))
    for index in range(count):
        next_index = (index + 1) % count
        faces.append(
            (
                base + index,
                base + next_index,
                base + count + next_index,
                base + count + index,
            )
        )


def add_box(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float],
    size: tuple[float, float],
    z_min: float,
    z_max: float,
) -> None:
    half_x, half_y = size[0] / 2, size[1] / 2
    outline = [
        (center[0] - half_x, center[1] - half_y),
        (center[0] + half_x, center[1] - half_y),
        (center[0] + half_x, center[1] + half_y),
        (center[0] - half_x, center[1] + half_y),
    ]
    add_prism(vertices, faces, outline, z_min, z_max)


def add_annular_cylinder(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float],
    outer_diameter: float,
    inner_diameter: float,
    z_min: float,
    z_max: float,
    segments: int = 32,
) -> None:
    base = len(vertices)
    outer_radius = outer_diameter / 2
    inner_radius = inner_diameter / 2
    for z in (z_min, z_max):
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append(
                    (
                        center[0] + math.cos(angle) * radius,
                        center[1] + math.sin(angle) * radius,
                        z,
                    )
                )
    bottom_outer = base
    bottom_inner = base + segments
    top_outer = base + segments * 2
    top_inner = base + segments * 3
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.extend(
            [
                (
                    bottom_outer + index,
                    bottom_outer + next_index,
                    top_outer + next_index,
                    top_outer + index,
                ),
                (
                    bottom_inner + next_index,
                    bottom_inner + index,
                    top_inner + index,
                    top_inner + next_index,
                ),
                (
                    top_outer + index,
                    top_outer + next_index,
                    top_inner + next_index,
                    top_inner + index,
                ),
                (
                    bottom_outer + next_index,
                    bottom_outer + index,
                    bottom_inner + index,
                    bottom_inner + next_index,
                ),
            ]
        )


def make_base_mesh(material: bpy.types.Material) -> bpy.types.Mesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    half_length = BODY_LENGTH / 2
    half_width = BODY_WIDTH / 2
    body_outline = [
        (-half_length, -2.20),
        (-0.50, -2.20),
        (0.10, -2.65),
        (0.70, -3.20),
        (1.30, -half_width),
        (4.10, -half_width),
        (half_length, -2.75),
        (half_length, 2.20),
        (0.50, 2.20),
        (-0.10, 2.65),
        (-0.70, 3.20),
        (-1.30, half_width),
        (-4.10, half_width),
        (-half_length, 2.75),
    ]
    add_prism(vertices, faces, body_outline, -BODY_HEIGHT, 0.0)
    for center in (LOCAL_CONTACT_A, LOCAL_CONTACT_B):
        add_annular_cylinder(
            vertices,
            faces,
            center,
            BOSS_OUTER_DIAMETER,
            BOSS_INNER_DIAMETER,
            0.0,
            BOSS_HEIGHT,
        )
    mesh = bpy.data.meshes.new("CPG135001S30_Nylon_Base_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    return mesh


def make_contact_mesh(material: bpy.types.Material) -> bpy.types.Mesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    terminal_extension = (TERMINAL_OVERALL_LENGTH - BODY_LENGTH) / 2
    terminal_length = terminal_extension + 0.55
    terminal_width = 1.68
    add_box(
        vertices,
        faces,
        (-BODY_LENGTH / 2 - terminal_extension / 2 + 0.275, LOCAL_CONTACT_A[1]),
        (terminal_length, terminal_width),
        -0.14,
        0.02,
    )
    add_box(
        vertices,
        faces,
        (BODY_LENGTH / 2 + terminal_extension / 2 - 0.275, LOCAL_CONTACT_B[1]),
        (terminal_length, terminal_width),
        -0.14,
        0.02,
    )
    # Paired spring fingers remain visible inside each 1.20 mm entry opening.
    for center in (LOCAL_CONTACT_A, LOCAL_CONTACT_B):
        for y_offset in (-0.28, 0.28):
            add_box(
                vertices,
                faces,
                (center[0], center[1] + y_offset),
                (0.92, 0.16),
                0.12,
                BOSS_HEIGHT - 0.16,
            )
    mesh = bpy.data.meshes.new("CPG135001S30_Copper_Contacts_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    return mesh


def bevel_shared_mesh(
    mesh: bpy.types.Mesh,
    collection: bpy.types.Collection,
    *,
    width: float,
    segments: int,
) -> bpy.types.Mesh:
    """Apply bevel once so all 45 instances can share the resulting mesh."""
    prototype = bpy.data.objects.new(f"_{mesh.name}_Bevel_Prototype", mesh)
    collection.objects.link(prototype)
    bpy.ops.object.select_all(action="DESELECT")
    prototype.select_set(True)
    bpy.context.view_layer.objects.active = prototype
    modifier = prototype.modifiers.new("Datasheet_Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    result = prototype.data
    bpy.data.objects.remove(prototype, do_unlink=True)
    return result


def switch_socket_footprints(data: dict) -> list[dict]:
    footprints = []
    for shape in data["shape"]:
        if not shape.startswith("LIB~"):
            continue
        chunks = shape.split("#@$")
        header = chunks[0].split("~")
        if len(header) < 4 or "package`CPG135001S30`" not in header[3]:
            continue
        contact_holes = []
        for chunk in chunks[1:]:
            parts = chunk.split("~")
            if parts[0] != "HOLE" or len(parts) < 4:
                continue
            radius_mm = float(parts[3]) * EASYEDA_TO_MM
            if abs(radius_mm - PCB_RECOMMENDED_HOLE_DIAMETER / 2) < 0.02:
                contact_holes.append(pcb_xy(float(parts[1]), float(parts[2])))
        if len(contact_holes) != 2:
            raise RuntimeError(
                f"CPG135001S30 footprint must contain two 3.00 mm holes: {header[:7]}"
            )
        contact_a, contact_b = contact_holes
        center = (
            (contact_a[0] + contact_b[0]) / 2,
            (contact_a[1] + contact_b[1]) / 2,
        )
        source_angle = math.atan2(CONTACT_OFFSET_Y, CONTACT_OFFSET_X)
        actual_angle = math.atan2(
            contact_b[1] - contact_a[1], contact_b[0] - contact_a[0]
        )
        footprints.append(
            {
                "center": center,
                "angle": actual_angle - source_angle,
                "contact_a": contact_a,
                "contact_b": contact_b,
                "source_id": header[6] if len(header) > 6 else "",
            }
        )
    return footprints


def mark_generated(obj: bpy.types.Object, side: str, role: str) -> None:
    obj["socket_generated"] = True
    obj["socket_side"] = side
    obj["socket_role"] = role
    obj["socket_part_number"] = "CPG135001S30"
    obj["socket_revision"] = REVISION
    obj["socket_datasheet"] = DATASHEET_RELATIVE_PATH


def create_socket_instances(
    side: str,
    footprints: list[dict],
    collection: bpy.types.Collection,
    half_root: bpy.types.Object,
    base_mesh: bpy.types.Mesh,
    contact_mesh: bpy.types.Mesh,
) -> tuple[bpy.types.Object, int]:
    assembly = bpy.data.objects.new(f"{side}_Sockets_Assembly", None)
    collection.objects.link(assembly)
    assembly.parent = half_root
    assembly.matrix_parent_inverse = Matrix.Identity(4)
    assembly.matrix_basis = Matrix.Identity(4)
    assembly["socket_assembly"] = True
    assembly["socket_count"] = len(footprints)
    mark_generated(assembly, side, "assembly")

    for index, footprint in enumerate(footprints, 1):
        prefix = f"{side}_Socket_{index:02d}"
        root = bpy.data.objects.new(prefix, None)
        collection.objects.link(root)
        root.parent = assembly
        root.matrix_parent_inverse = Matrix.Identity(4)
        root.location = (
            footprint["center"][0],
            footprint["center"][1],
            BOARD_BOTTOM_Z - SOCKET_TOP_CLEARANCE,
        )
        root.rotation_euler[2] = footprint["angle"]
        root["component_type"] = "Kailh Choc hot-swap socket"
        root["socket_index"] = index
        root["socket_contact_a_pcb_mm"] = list(footprint["contact_a"])
        root["socket_contact_b_pcb_mm"] = list(footprint["contact_b"])
        root["socket_body_length_mm"] = BODY_LENGTH
        root["socket_body_width_mm"] = BODY_WIDTH
        root["socket_overall_length_mm"] = TERMINAL_OVERALL_LENGTH
        root["socket_overall_height_mm"] = OVERALL_HEIGHT
        root["socket_boss_outer_diameter_mm"] = BOSS_OUTER_DIAMETER
        root["socket_recommended_pcb_hole_mm"] = PCB_RECOMMENDED_HOLE_DIAMETER
        root["socket_source_id"] = footprint["source_id"]
        mark_generated(root, side, "socket")

        base = bpy.data.objects.new(f"{prefix}_Base", base_mesh)
        contacts = bpy.data.objects.new(f"{prefix}_Contacts", contact_mesh)
        for obj, role in ((base, "nylon_base"), (contacts, "copper_contacts")):
            collection.objects.link(obj)
            obj.parent = root
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj.matrix_basis = Matrix.Identity(4)
            mark_generated(obj, side, role)
    return assembly, len(footprints)


def setup_exploded_view(enabled: bool, spacing: float) -> dict:
    module_path = Path(__file__).with_name("setup_assembly_exploded_view.py")
    spec = importlib.util.spec_from_file_location("akdk_exploded_setup", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.setup_exploded_view(enabled=enabled, spacing_mm=spacing)


def build_sockets(*, save: bool = True, setup_exploded: bool = True) -> dict:
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    keyboard_collection = bpy.data.collections.get("Keyboard_Model")
    keyboard_root = bpy.data.objects.get("Keyboard_Root")
    if keyboard_collection is None or keyboard_root is None:
        raise RuntimeError("Keyboard_Model or Keyboard_Root is missing")

    collection = ensure_collection(COLLECTION_NAME, keyboard_collection)
    clean_generated(collection)
    nylon = ensure_material(
        "Socket_Nylon_Black", (0.010, 0.014, 0.018, 1.0), roughness=0.34
    )
    copper = ensure_material(
        "Socket_Copper_Alloy",
        (0.62, 0.27, 0.055, 1.0),
        roughness=0.24,
        metallic=0.82,
    )
    base_mesh = bevel_shared_mesh(
        make_base_mesh(nylon), collection, width=0.12, segments=3
    )
    contact_mesh = bevel_shared_mesh(
        make_contact_mesh(copper), collection, width=0.035, segments=2
    )

    summaries = {}
    total = 0
    for side in ("Left", "Right"):
        half_root = bpy.data.objects.get(f"{side}_Half_Root")
        if half_root is None:
            raise RuntimeError(f"Missing {side}_Half_Root")
        data_path = PCB_DIR / f"Surround1x0-AKDK-{side.lower()}-pcb.json"
        data = json.loads(data_path.read_text())
        footprints = switch_socket_footprints(data)
        _assembly, count = create_socket_instances(
            side, footprints, collection, half_root, base_mesh, contact_mesh
        )
        total += count
        summaries[side] = {
            "source": str(data_path.relative_to(ROOT)),
            "socket_count": count,
        }

    keyboard_root["socket_model_part_number"] = "CPG135001S30"
    keyboard_root["socket_model_revision"] = REVISION
    keyboard_root["socket_model_datasheet"] = DATASHEET_RELATIVE_PATH
    keyboard_root["socket_model_count"] = total
    keyboard_root["socket_model_dimensions_mm"] = (
        f"body={BODY_LENGTH}x{BODY_WIDTH}x{BODY_HEIGHT}; "
        f"overall_length={TERMINAL_OVERALL_LENGTH}; overall_height={OVERALL_HEIGHT}; "
        f"boss_od={BOSS_OUTER_DIAMETER}; pcb_hole={PCB_RECOMMENDED_HOLE_DIAMETER}"
    )

    exploded_summary = None
    if setup_exploded:
        enabled = bool(keyboard_root.get("exploded_view_enabled", True))
        spacing = float(keyboard_root.get("exploded_view_spacing_mm", 30.0))
        exploded_summary = setup_exploded_view(enabled=enabled, spacing=spacing)

    if save:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    return {
        "revision": REVISION,
        "part_number": "CPG135001S30",
        "datasheet": DATASHEET_RELATIVE_PATH,
        "socket_count": total,
        "sides": summaries,
        "dimensions_mm": {
            "body_length": BODY_LENGTH,
            "body_width": BODY_WIDTH,
            "body_height": BODY_HEIGHT,
            "overall_length": TERMINAL_OVERALL_LENGTH,
            "overall_height": OVERALL_HEIGHT,
            "boss_outer_diameter": BOSS_OUTER_DIAMETER,
            "pcb_hole_diameter": PCB_RECOMMENDED_HOLE_DIAMETER,
            "contact_offset_x": CONTACT_OFFSET_X,
            "contact_offset_y": abs(CONTACT_OFFSET_Y),
        },
        "exploded_view": exploded_summary,
    }


if __name__ == "__main__":
    print(
        "SOCKET_BUILD_RESULT="
        + json.dumps(build_sockets(), ensure_ascii=False, sort_keys=True)
    )
