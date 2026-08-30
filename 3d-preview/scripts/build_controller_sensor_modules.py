"""Build the Auto-KDK wireless controllers, conthrough pins and mouse sensor.

The dimensions and placement anchors come from three repository-owned sources:

* the Auto-KDK documentation photographs and the controller keep-out footprint
  embedded in this keyboard's EasyEDA JSON;
* the 9-pin/1.27 mm/H=2.5 mm conthrough specification in Auto-KDK;
* the 13.4 x 7.4 mm drawing in small-mouse-sensor-module.

Every assembly remains separate from the main PCB so it can be isolated in the
web preview and moved independently by the assembly-level Exploded View.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = ROOT / "3d-preview/Surround1x0-AKDK.blend"
PCB_DIR = ROOT / "pcb"
COLLECTION_NAME = "02e_Controller_Sensor"
REVISION = "auto-kdk-controller-sensor-v8-usb-c-centered"

AUTO_KDK_SOURCE = "https://github.com/sekigon-gonnoc/auto-kdk"
SENSOR_SOURCE = "https://github.com/sekigon-gonnoc/small-mouse-sensor-module"
PHOTO_SOURCE = "user-supplied IMG_2679..IMG_2688 reference photos"

EASYEDA_TO_MM = 0.254
PCB_X_OFFSET_MM = -108.75
PCB_Y_OFFSET_MM = 91.8
MAIN_PCB_CENTER_Z = -1.85
MAIN_PCB_THICKNESS = 1.60
MAIN_PCB_TOP_Z = MAIN_PCB_CENTER_Z + MAIN_PCB_THICKNESS / 2
MAIN_PCB_BOTTOM_Z = MAIN_PCB_CENTER_Z - MAIN_PCB_THICKNESS / 2
MAIN_PCB_SOLDER_MASK_COLOR = (0.012, 0.028, 0.024, 1.0)
MAIN_PCB_SOLDER_MASK_ROUGHNESS = 0.28

# The red cut lines in wireless-controller-cut.png span 740 px while the full
# placement envelope spans 249 px.  Anchoring that ratio to the 29 mm EasyEDA
# courtyard yields 86.18 mm.  The courtyard includes the USB-C overhang; it is
# not the green PCB outline.  The actual PCB stops behind the lower-case wall so
# only the connector enters the side aperture.
CONTROLLER_LENGTH = 86.20
CONTROLLER_WIDTH = 25.40
CONTROLLER_KEEP_OUT_WIDTH = 29.00
CONTROLLER_THICKNESS = 1.60
CONTROLLER_GAP = 2.50
# Auto-KDK is mounted component-side down below the main PCB.  The 2.5 mm
# conthrough height is the clear vertical span between the two PCB surfaces.
CONTROLLER_TOP_Z = MAIN_PCB_BOTTOM_Z - CONTROLLER_GAP
CONTROLLER_BOTTOM_Z = CONTROLLER_TOP_Z - CONTROLLER_THICKNESS
CONTROLLER_Y_MIN = 30.30
CONTROLLER_Y_MAX = CONTROLLER_Y_MIN + CONTROLLER_WIDTH
CONTROLLER_KEEP_OUT_Y_MAX = CONTROLLER_Y_MIN + CONTROLLER_KEEP_OUT_WIDTH
CONTROLLER_CASE_WALL_RECESS = 0.98
CONTROLLER_NOTCH_X0 = 39.10
CONTROLLER_NOTCH_X1 = 48.70
CONTROLLER_NOTCH_DEPTH = 12.10

CONTHROUGH_PIN_COUNT = 9
CONTHROUGH_PITCH = 1.27
CONTHROUGH_ROW_SEPARATION = 19.00
CONTHROUGH_BODY_HEIGHT = 2.50
CONTHROUGH_BODY_WIDTH = 1.15
CONTHROUGH_BODY_LENGTH = 11.40
CONTHROUGH_WIRE_DIAMETER = 0.30
CONTHROUGH_HOLE_DIAMETER = 0.70

SENSOR_LENGTH = 13.40
SENSOR_WIDTH = 7.40
SENSOR_THICKNESS = 1.00
SENSOR_SLOT_LENGTH = 2.20
SENSOR_SLOT_WIDTH = 0.75
FPC_PITCH = 0.50
FPC_PIN_COUNT = 6
FPC_WIDTH = FPC_PITCH * FPC_PIN_COUNT
FPC_THICKNESS = 0.12

TRACKBALL_CENTER = Vector((-2.375, -31.875, 9.925))
TRACKBALL_RADIUS = 17.0
SENSOR_TANGENT_ANGLE_DEG = -60.0
SENSOR_IN_PLANE_ANGLE_DEG = 180.0
# Measured from the right top-case mesh.  The lens passes through the narrow
# aperture at the ball's +X side; the neighboring +Y groove carries the FPC
# toward the Auto-KDK controller.
SENSOR_LENS_TARGET = Vector((12.700, -31.875, 1.400))
SENSOR_UPPER_LENS_LOCAL = Vector((0.0, 2.35, 1.82))
SENSOR_FPC_CONNECTOR_LOCAL = Vector((0.0, -4.75, 1.05))
SENSOR_FPC_GROOVE_Y = -23.35

# Case openings are verification envelopes, not placement constraints.  The
# Auto-KDK PCB is registered by its two selected 9-pin conthrough rows from the
# repository EasyEDA footprint.  USB-C intentionally sits within the wider
# case aperture so a cable plug can enter without over-constraining the board.
CASE_USB_X = {"Left": 4.75, "Right": -4.75}
CASE_USB_APERTURE_X = {
    "Left": (-2.75, 12.25),
    "Right": (-12.25, 2.75),
}
CASE_USB_APERTURE_Z = (-11.45, -3.45)
CASE_USB_WALL_Y = {"Left": 56.697, "Right": 56.683}
USB_C_SHELL_WIDTH = 8.90
USB_C_SHELL_HEIGHT = 3.25
USB_C_SHELL_DEPTH = 6.20
USB_C_SHELL_RADIUS = 1.28
USB_C_MOUTH_DEPTH = 0.24
# The visible metal lip sits behind the lower-case outer wall; it must never
# protrude from the enclosure.  Use the shallower wall coordinate so the
# symmetric left/right receptacles both retain at least this recess.
USB_C_FACE_RECESS = 0.35
USB_C_SHELL_FRONT_Y = min(CASE_USB_WALL_Y.values()) - USB_C_MOUTH_DEPTH - USB_C_FACE_RECESS
# USB Type-C Cable and Connector Specification R2.0, Figure 3-1.
USB_C_SHELL_OPENING_WIDTH = 8.34
USB_C_SHELL_OPENING_HEIGHT = 2.56
USB_C_SHELL_OPENING_RADIUS = USB_C_SHELL_OPENING_HEIGHT / 2
USB_C_CAVITY_WIDTH = 8.20
USB_C_CAVITY_HEIGHT = 2.42
USB_C_CAVITY_RADIUS = USB_C_CAVITY_HEIGHT / 2
USB_C_TONGUE_WIDTH = 6.20
USB_C_TONGUE_HEIGHT = 0.46
USB_C_TONGUE_RADIUS = 0.20
USB_C_CONTACT_COUNT_PER_SIDE = 12
USB_C_CONTACT_PITCH = 0.50
CASE_POWER_SLOT_CENTER = {
    "Left": (9.25, 28.50),
    "Right": (-9.25, 28.50),
}
CASE_POWER_SLOT_X = {
    "Left": (8.00, 10.50),
    "Right": (-10.50, -8.00),
}
CASE_POWER_SLOT_Y = (25.25, 31.75)
CASE_POWER_SLOT_Z = (-11.70, -10.00)
CASE_CONTROLLER_SUPPORT_Z = -11.70
# Rail-free board extents, derived from the 98 mm EasyEDA courtyard and
# the official red cut lines.  These values preserve the exact relationship
# between the board outline and the selected conthrough rows.
BOARD_X_MIN = {
    "Left": -54.50,
    "Right": -26.75,
}


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
    prefixes = (
        "Left_Controller",
        "Right_Controller",
        "Left_Conthrough",
        "Right_Conthrough",
        "Right_Mouse_Sensor",
    )
    for obj in list(collection.all_objects):
        if obj.get("controller_sensor_generated") is True or obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.curves):
        for datablock in list(datablocks):
            if datablock.users == 0 and datablock.name.startswith(
                ("AutoKDK_", "Conthrough_", "MouseSensor_", "SensorFPC_")
            ):
                datablocks.remove(datablock)


def ensure_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float,
    metallic: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    material.surface_render_method = "DITHERED" if alpha < 1.0 else "DITHERED"
    bsdf = next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
    material["controller_sensor_generated"] = True
    return material


def mark_generated(
    obj: bpy.types.Object,
    side: str,
    role: str,
    component: str,
) -> bpy.types.Object:
    obj["controller_sensor_generated"] = True
    obj["controller_sensor_revision"] = REVISION
    obj["component_side"] = side
    obj["component_role"] = role
    obj["component_family"] = component
    return obj


def add_prism_geometry(
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
        nxt = (index + 1) % count
        faces.append((base + index, base + nxt, base + count + nxt, base + count + index))


def create_prism(
    name: str,
    outline: list[tuple[float, float]],
    z_min: float,
    z_max: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    add_prism_geometry(vertices, faces, outline, z_min, z_max)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def create_box(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    bevel: float = 0.0,
    segments: int = 2,
) -> bpy.types.Object:
    cx, cy, cz = center
    sx, sy, sz = size
    outline = [
        (cx - sx / 2, cy - sy / 2),
        (cx + sx / 2, cy - sy / 2),
        (cx + sx / 2, cy + sy / 2),
        (cx - sx / 2, cy + sy / 2),
    ]
    obj = create_prism(name, outline, cz - sz / 2, cz + sz / 2, collection, material)
    if bevel > 0:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new("Manufactured_Edge_Radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def rounded_rect_xz_points(
    center_x: float,
    center_z: float,
    width: float,
    height: float,
    radius: float,
    *,
    segments_per_corner: int = 8,
) -> list[tuple[float, float]]:
    radius = min(radius, width / 2, height / 2)
    corners = (
        (center_x + width / 2 - radius, center_z + height / 2 - radius, 0.0),
        (center_x - width / 2 + radius, center_z + height / 2 - radius, 90.0),
        (center_x - width / 2 + radius, center_z - height / 2 + radius, 180.0),
        (center_x + width / 2 - radius, center_z - height / 2 + radius, 270.0),
    )
    points = []
    for corner_x, corner_z, start_degrees in corners:
        for index in range(segments_per_corner):
            angle = math.radians(start_degrees + 90.0 * index / segments_per_corner)
            points.append(
                (
                    corner_x + math.cos(angle) * radius,
                    corner_z + math.sin(angle) * radius,
                )
            )
    return points


def create_xz_prism(
    name: str,
    outline: list[tuple[float, float]],
    y_min: float,
    y_max: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    count = len(outline)
    vertices = [(x, y_min, z) for x, z in outline]
    vertices.extend((x, y_max, z) for x, z in outline)
    faces = [
        tuple(range(count)),
        tuple(count + index for index in reversed(range(count))),
    ]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, count + index, count + nxt, nxt))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def create_xz_ring(
    name: str,
    outer: list[tuple[float, float]],
    inner: list[tuple[float, float]],
    y_min: float,
    y_max: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    if len(outer) != len(inner):
        raise ValueError("USB-C shell ring outlines must have matching vertex counts")
    count = len(outer)
    vertices = [(x, y_min, z) for x, z in outer]
    vertices.extend((x, y_min, z) for x, z in inner)
    vertices.extend((x, y_max, z) for x, z in outer)
    vertices.extend((x, y_max, z) for x, z in inner)
    faces = []
    for index in range(count):
        nxt = (index + 1) % count
        outer_back = index
        inner_back = count + index
        outer_front = count * 2 + index
        inner_front = count * 3 + index
        outer_back_next = nxt
        inner_back_next = count + nxt
        outer_front_next = count * 2 + nxt
        inner_front_next = count * 3 + nxt
        faces.extend(
            (
                (outer_back, outer_back_next, inner_back_next, inner_back),
                (outer_front, inner_front, inner_front_next, outer_front_next),
                (outer_back, outer_front, outer_front_next, outer_back_next),
                (inner_back, inner_back_next, inner_front_next, inner_front),
            )
        )
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def add_cylinder(
    name: str,
    center: tuple[float, float, float],
    radius: float,
    depth: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def parent_local(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)


def controller_footprint(side: str) -> dict:
    data = json.loads((PCB_DIR / f"Surround1x0-AKDK-{side.lower()}-pcb.json").read_text())
    target = None
    for shape in data["shape"]:
        if shape.startswith("LIB~") and "package`MS88SF2" in shape.split("#@$")[0]:
            target = shape
            break
    if target is None:
        raise RuntimeError(f"Auto-KDK controller footprint missing from {side} PCB")
    chunks = target.split("#@$")
    header = chunks[0].split("~")
    pads = []
    for chunk in chunks[1:]:
        parts = chunk.split("~")
        if parts[0] != "PAD" or len(parts) < 10 or parts[6] != "11":
            continue
        pads.append(
            {
                "number": int(parts[8]),
                "center": pcb_xy(float(parts[2]), float(parts[3])),
                "hole_diameter": float(parts[9]) * EASYEDA_TO_MM * 2,
            }
        )
    if len(pads) != CONTHROUGH_PIN_COUNT * 2:
        raise RuntimeError(f"Expected 18 controller pads on {side}, found {len(pads)}")
    rows: dict[float, list[dict]] = {}
    for pad in pads:
        rows.setdefault(round(pad["center"][0], 3), []).append(pad)
    ordered_rows = [sorted(row, key=lambda item: item["center"][1]) for row in rows.values()]
    ordered_rows.sort(key=lambda row: row[0]["center"][0])
    if len(ordered_rows) != 2 or any(len(row) != CONTHROUGH_PIN_COUNT for row in ordered_rows):
        raise RuntimeError(f"Unexpected controller pad rows for {side}: {rows.keys()}")
    separation = abs(ordered_rows[1][0]["center"][0] - ordered_rows[0][0]["center"][0])
    pitches = [
        b["center"][1] - a["center"][1]
        for row in ordered_rows
        for a, b in zip(row, row[1:])
    ]
    return {
        "package": header[3].split("package`")[1].split("`")[0],
        "pads": pads,
        "rows": ordered_rows,
        "row_separation": separation,
        "pitch": sum(abs(value) for value in pitches) / len(pitches),
    }


def board_outline(side: str) -> list[tuple[float, float]]:
    xmin = BOARD_X_MIN[side]
    xmax = xmin + CONTROLLER_LENGTH
    if side == "Left":
        notch0 = xmin + CONTROLLER_NOTCH_X0
        notch1 = xmin + CONTROLLER_NOTCH_X1
    else:
        notch0 = xmin + CONTROLLER_LENGTH - CONTROLLER_NOTCH_X1
        notch1 = xmin + CONTROLLER_LENGTH - CONTROLLER_NOTCH_X0
    return [
        (xmin, CONTROLLER_Y_MIN),
        (notch0, CONTROLLER_Y_MIN),
        (notch0, CONTROLLER_Y_MIN + CONTROLLER_NOTCH_DEPTH),
        (notch1, CONTROLLER_Y_MIN + CONTROLLER_NOTCH_DEPTH),
        (notch1, CONTROLLER_Y_MIN),
        (xmax, CONTROLLER_Y_MIN),
        (xmax, CONTROLLER_Y_MAX),
        (xmin, CONTROLLER_Y_MAX),
    ]


def cut_circular_holes(
    obj: bpy.types.Object,
    holes: list[tuple[tuple[float, float], float]],
    collection: bpy.types.Collection,
    name: str,
) -> None:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    z_min = CONTROLLER_BOTTOM_Z - 1
    z_max = CONTROLLER_TOP_Z + 1
    segments = 20
    for (cx, cy), diameter in holes:
        outline = [
            (
                cx + math.cos(math.tau * index / segments) * diameter / 2,
                cy + math.sin(math.tau * index / segments) * diameter / 2,
            )
            for index in range(segments)
        ]
        add_prism_geometry(vertices, faces, outline, z_min, z_max)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cutter = bpy.data.objects.new(name, mesh)
    collection.objects.link(cutter)
    modifier = obj.modifiers.new("Actual_Conthrough_Holes", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def create_annular_pads(
    name: str,
    pads: list[dict],
    z: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    segments = 20
    outer_radius = 0.65
    for pad in pads:
        cx, cy = pad["center"]
        inner_radius = max(0.20, pad["hole_diameter"] / 2)
        base = len(vertices)
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius, z))
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((base + index, base + nxt, base + segments + nxt, base + segments + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def component_x(side: str, relative_x: float) -> float:
    """Map photo-derived component X from the conthrough-registered board."""
    if side == "Left":
        return BOARD_X_MIN[side] + relative_x
    return BOARD_X_MIN[side] + CONTROLLER_LENGTH - relative_x


def selected_conthrough_center_x(footprint: dict) -> float:
    return sum(pad["center"][0] for pad in footprint["pads"]) / len(footprint["pads"])


def controller_board_holes(side: str, footprint: dict) -> list[dict]:
    """Return the 45 physical holes: 18 selected + 27 pitch alternatives.

    Auto-KDK uses the outer rows for 19 mm pitch.  Three additional columns at
    1 mm increments allow 18/17/16 mm switch pitch, as shown in the official
    board photograph and assembly documentation.
    """
    holes = [dict(pad) for pad in footprint["pads"]]
    grid_row = footprint["rows"][0 if side == "Left" else 1]
    inward = 1.0 if side == "Left" else -1.0
    for offset_index in (1, 2, 3):
        for pad in grid_row:
            variant = dict(pad)
            variant["center"] = (
                pad["center"][0] + inward * offset_index,
                pad["center"][1],
            )
            variant["pitch_variant_mm"] = 19 - offset_index
            holes.append(variant)
    return holes


def create_component_box(
    side: str,
    assembly: bpy.types.Object,
    collection: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
    suffix: str,
    relative_x: float,
    y: float,
    z_height: float,
    size_xy: tuple[float, float],
    material: str,
    *,
    bevel: float = 0.15,
    stack_below: float = 0.0,
    absolute_x: float | None = None,
) -> bpy.types.Object:
    obj = create_box(
        f"{side}_Controller_{suffix}",
        (
            component_x(side, relative_x) if absolute_x is None else absolute_x,
            y,
            CONTROLLER_BOTTOM_Z - stack_below - z_height / 2,
        ),
        (size_xy[0], size_xy[1], z_height),
        collection,
        materials[material],
        bevel=bevel,
    )
    parent_local(obj, assembly)
    return mark_generated(obj, side, suffix.lower(), "controller")


def append_box_geometry(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    center: tuple[float, float, float],
    size: tuple[float, float, float],
) -> None:
    cx, cy, cz = center
    sx, sy, sz = size
    base = len(vertices)
    vertices.extend(
        (
            (cx - sx / 2, cy - sy / 2, cz - sz / 2),
            (cx + sx / 2, cy - sy / 2, cz - sz / 2),
            (cx + sx / 2, cy + sy / 2, cz - sz / 2),
            (cx - sx / 2, cy + sy / 2, cz - sz / 2),
            (cx - sx / 2, cy - sy / 2, cz + sz / 2),
            (cx + sx / 2, cy - sy / 2, cz + sz / 2),
            (cx + sx / 2, cy + sy / 2, cz + sz / 2),
            (cx - sx / 2, cy + sy / 2, cz + sz / 2),
        )
    )
    faces.extend(
        tuple(base + index for index in face)
        for face in (
            (0, 3, 2, 1),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        )
    )


def create_usb_c_receptacle(
    side: str,
    assembly: bpy.types.Object,
    collection: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
    center_x: float,
) -> bpy.types.Object:
    center_z = CONTROLLER_BOTTOM_Z - USB_C_SHELL_HEIGHT / 2
    shell_front_y = USB_C_SHELL_FRONT_Y
    shell_back_y = shell_front_y - USB_C_SHELL_DEPTH
    shell_outline = rounded_rect_xz_points(
        center_x,
        center_z,
        USB_C_SHELL_WIDTH,
        USB_C_SHELL_HEIGHT,
        USB_C_SHELL_RADIUS,
    )
    opening_outline = rounded_rect_xz_points(
        center_x,
        center_z,
        USB_C_SHELL_OPENING_WIDTH,
        USB_C_SHELL_OPENING_HEIGHT,
        USB_C_SHELL_OPENING_RADIUS,
    )
    shell = create_xz_ring(
        f"{side}_Controller_USB_C",
        shell_outline,
        opening_outline,
        shell_back_y,
        shell_front_y,
        collection,
        materials["metal"],
    )
    shell["connector_type"] = "USB Type-C receptacle"
    shell["usb_c_part"] = "outer_shell"
    shell["shell_opening_width_mm"] = USB_C_SHELL_OPENING_WIDTH
    shell["shell_length_mm"] = 6.20
    parent_local(shell, assembly)
    mark_generated(shell, side, "usb_c", "controller")

    mouth = create_xz_ring(
        f"{side}_Controller_USB_C_Mouth",
        shell_outline,
        opening_outline,
        shell_front_y,
        shell_front_y + USB_C_MOUTH_DEPTH,
        collection,
        materials["metal"],
    )
    mouth["usb_c_part"] = "shell_mouth"
    mouth["opening_width_mm"] = USB_C_SHELL_OPENING_WIDTH
    mouth["opening_height_mm"] = USB_C_SHELL_OPENING_HEIGHT
    parent_local(mouth, assembly)
    mark_generated(mouth, side, "usb_c_mouth", "controller")

    cavity_outline = rounded_rect_xz_points(
        center_x,
        center_z,
        USB_C_CAVITY_WIDTH,
        USB_C_CAVITY_HEIGHT,
        USB_C_CAVITY_RADIUS,
    )
    cavity = create_xz_prism(
        f"{side}_Controller_USB_C_Cavity",
        cavity_outline,
        shell_front_y + 0.04,
        shell_front_y + 0.15,
        collection,
        materials["usb_cavity"],
    )
    cavity["usb_c_part"] = "receptacle_cavity"
    parent_local(cavity, assembly)
    mark_generated(cavity, side, "usb_c_cavity", "controller")

    tongue_outline = rounded_rect_xz_points(
        center_x,
        center_z,
        USB_C_TONGUE_WIDTH,
        USB_C_TONGUE_HEIGHT,
        USB_C_TONGUE_RADIUS,
        segments_per_corner=5,
    )
    tongue = create_xz_prism(
        f"{side}_Controller_USB_C_Tongue",
        tongue_outline,
        shell_front_y - 1.20,
        shell_front_y + 0.18,
        collection,
        materials["usb_tongue"],
    )
    tongue["usb_c_part"] = "center_tongue"
    parent_local(tongue, assembly)
    mark_generated(tongue, side, "usb_c_tongue", "controller")

    contact_vertices: list[tuple[float, float, float]] = []
    contact_faces: list[tuple[int, ...]] = []
    first_contact_x = center_x - USB_C_CONTACT_PITCH * (USB_C_CONTACT_COUNT_PER_SIDE - 1) / 2
    for row_z in (center_z - 0.19, center_z + 0.19):
        for index in range(USB_C_CONTACT_COUNT_PER_SIDE):
            append_box_geometry(
                contact_vertices,
                contact_faces,
                (
                    first_contact_x + index * USB_C_CONTACT_PITCH,
                    shell_front_y + 0.205,
                    row_z,
                ),
                (0.22, 0.045, 0.055),
            )
    contact_mesh = bpy.data.meshes.new(f"{side}_Controller_USB_C_Contacts_Mesh")
    contact_mesh.from_pydata(contact_vertices, [], contact_faces)
    contact_mesh.materials.append(materials["usb_contact"])
    contact_mesh.update()
    contacts = bpy.data.objects.new(f"{side}_Controller_USB_C_Contacts", contact_mesh)
    collection.objects.link(contacts)
    contacts["usb_c_part"] = "signal_contacts"
    contacts["contact_count"] = USB_C_CONTACT_COUNT_PER_SIDE * 2
    contacts["contact_pitch_mm"] = USB_C_CONTACT_PITCH
    parent_local(contacts, assembly)
    mark_generated(contacts, side, "usb_c_contacts", "controller")
    return shell


def create_battery_label(
    side: str,
    battery: bpy.types.Object,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"AutoKDK_{side}_Battery_Label_Curve", "FONT")
    curve.body = "LiPo 3.7V 400mAh\nDTP502535"
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 1.55
    curve.extrude = 0.008
    curve.resolution_u = 2
    label = bpy.data.objects.new(f"{side}_Controller_Battery_Label", curve)
    collection.objects.link(label)
    coordinates = [vertex.co for vertex in battery.data.vertices]
    minimum = [min(vertex[index] for vertex in coordinates) for index in range(3)]
    maximum = [max(vertex[index] for vertex in coordinates) for index in range(3)]
    label.location = (
        (minimum[0] + maximum[0]) / 2,
        (minimum[1] + maximum[1]) / 2,
        minimum[2] - 0.035,
    )
    label.rotation_euler[0] = math.pi
    curve.materials.append(material)
    parent_local(label, battery.parent)
    return mark_generated(label, side, "battery_label", "controller")


def create_controller(
    side: str,
    footprint: dict,
    collection: bpy.types.Collection,
    half_root: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    assembly = bpy.data.objects.new(f"{side}_Controller_Assembly", None)
    collection.objects.link(assembly)
    parent_local(assembly, half_root)
    assembly["controller_assembly"] = True
    assembly["controller_model"] = "Auto-KDK wireless controller"
    assembly["controller_source"] = AUTO_KDK_SOURCE
    assembly["controller_dimensions_mm"] = [CONTROLLER_LENGTH, CONTROLLER_WIDTH, CONTROLLER_THICKNESS]
    assembly["controller_keep_out_dimensions_mm"] = [
        CONTROLLER_LENGTH,
        CONTROLLER_KEEP_OUT_WIDTH,
        CONTROLLER_THICKNESS,
    ]
    assembly["controller_easyeda_package"] = footprint["package"]
    assembly["controller_mounting_side"] = "below main PCB, component side down"
    assembly["controller_placement_anchor"] = "selected 19 mm conthrough rows from EasyEDA footprint"
    assembly["selected_conthrough_center_x_mm"] = selected_conthrough_center_x(footprint)
    assembly["case_usb_clearance_reference_mm"] = [CASE_USB_X[side], CASE_USB_WALL_Y[side]]
    assembly["case_power_slot_anchor_mm"] = list(CASE_POWER_SLOT_CENTER[side])
    mark_generated(assembly, side, "assembly", "controller")

    board = create_prism(
        f"{side}_Controller_PCB",
        board_outline(side),
        CONTROLLER_BOTTOM_Z,
        CONTROLLER_TOP_Z,
        collection,
        materials["controller_pcb"],
    )
    board_holes = controller_board_holes(side, footprint)
    cut_circular_holes(
        board,
        [(pad["center"], CONTHROUGH_HOLE_DIAMETER) for pad in board_holes],
        collection,
        f"AutoKDK_{side}_Controller_Hole_Cutters",
    )
    board["actual_through_holes"] = len(board_holes)
    board["selected_conthrough_holes"] = len(footprint["pads"])
    board["available_pitch_variants_mm"] = [19, 18, 17, 16]
    parent_local(board, assembly)
    mark_generated(board, side, "pcb", "controller")

    for face, z in (("Top", CONTROLLER_TOP_Z + 0.015), ("Bottom", CONTROLLER_BOTTOM_Z - 0.015)):
        pads = create_annular_pads(
            f"{side}_Controller_Conthrough_Pads_{face}",
            board_holes,
            z,
            collection,
            materials["pad"],
        )
        parent_local(pads, assembly)
        mark_generated(pads, side, f"conthrough_pads_{face.lower()}", "controller")

    rf_pcb = create_component_box(
        side, assembly, collection, materials, "RF_Module_PCB", 76.2, 44.3, 0.75, (18.0, 21.0), "dark_pcb", bevel=0.10
    )
    shield = create_component_box(
        side, assembly, collection, materials, "RF_Shield", 76.0, 43.3, 1.15, (14.6, 14.7), "metal", bevel=0.35,
        stack_below=0.75,
    )
    antenna = create_component_box(
        side, assembly, collection, materials, "RF_Antenna", 76.0, 52.7, 1.15, (15.5, 5.8), "black", bevel=0.20,
        stack_below=0.75,
    )
    for obj in (rf_pcb, shield, antenna):
        obj["rf_soc"] = "nRF52840"

    # The connector is registered to the centre of the lower-case aperture.
    # It is not concentric with the selected conthrough rows on this PCB.
    create_usb_c_receptacle(side, assembly, collection, materials, CASE_USB_X[side])

    jst = create_component_box(
        side, assembly, collection, materials, "JST_PH_2P", 52.2, 34.9, 4.10, (7.6, 8.4), "white", bevel=0.25
    )
    jst["connector_type"] = "JST PH 2-pin"
    jst["battery_voltage"] = "1S LiPo 3.7V"
    power = create_component_box(
        side, assembly, collection, materials, "Power_Switch", 0.0, 34.8, 3.15,
        (5.2, 8.2), "black", bevel=0.18,
        absolute_x=CASE_POWER_SLOT_CENTER[side][0],
    )
    power["component_type"] = "slide power switch"
    actuator = create_component_box(
        side, assembly, collection, materials, "Power_Switch_Actuator", 61.0, 28.50, 2.80,
        (2.10, 5.80), "black", bevel=0.16, stack_below=2.30,
        absolute_x=CASE_POWER_SLOT_CENTER[side][0],
    )
    actuator["component_type"] = "slide power switch actuator through lower-case slot"
    fpc = create_component_box(
        side, assembly, collection, materials, "FPC_6P_Connector", 81.7, 33.5, 1.55, (6.4, 3.0), "white", bevel=0.10
    )
    fpc["connector_type"] = "0.5 mm pitch 6-pin FPC"

    for index, (relative_x, y, sx, sy) in enumerate(
        (
            (59.0, 45.0, 4.1, 3.4),
            (63.9, 45.8, 2.5, 2.2),
            (68.1, 35.3, 2.8, 2.1),
            (72.1, 35.0, 1.8, 1.3),
            (76.3, 35.0, 2.3, 1.5),
        ),
        1,
    ):
        chip = create_component_box(
            side, assembly, collection, materials, f"SMD_{index:02d}", relative_x, y, 0.75, (sx, sy), "black", bevel=0.08
        )
        chip["component_type"] = "controller SMD"

    battery = create_component_box(
        side, assembly, collection, materials, "LiPo_400mAh", 19.2, 43.0, 5.0, (35.0, 25.0), "battery", bevel=1.2
    )
    battery["battery_model"] = "DTP502535(PHR)"
    battery["battery_capacity_mAh"] = 400
    battery["battery_voltage_V"] = 3.7
    create_battery_label(side, battery, collection, materials["label"])

    # Short insulated lead from LiPo pouch to the JST PH connector.
    cable_points = [
        (component_x(side, 36.5), 43.0, CONTROLLER_BOTTOM_Z - 2.8),
        (component_x(side, 42.0), 40.5, CONTROLLER_BOTTOM_Z - 2.4),
        (component_x(side, 48.5), 35.4, CONTROLLER_BOTTOM_Z - 2.2),
    ]
    for color_name, offset in (("red", -0.42), ("black", 0.42)):
        curve = bpy.data.curves.new(f"AutoKDK_{side}_Battery_{color_name}_Curve", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2
        curve.bevel_depth = 0.22
        curve.bevel_resolution = 2
        spline = curve.splines.new("POLY")
        spline.points.add(len(cable_points) - 1)
        for point, coordinate in zip(spline.points, cable_points):
            point.co = (coordinate[0], coordinate[1] + offset, coordinate[2], 1.0)
        wire = bpy.data.objects.new(f"{side}_Controller_Battery_Wire_{color_name.title()}", curve)
        collection.objects.link(wire)
        curve.materials.append(materials[color_name])
        parent_local(wire, assembly)
        mark_generated(wire, side, f"battery_wire_{color_name}", "controller")
    return assembly


def create_conthrough_wire_curve(
    name: str,
    x: float,
    y: float,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"Conthrough_{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = CONTHROUGH_WIRE_DIAMETER / 2
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    points = [
        (x - 0.38, y, MAIN_PCB_TOP_Z + 0.85),
        (x - 0.38, y, CONTROLLER_BOTTOM_Z - 0.85),
        (x + 0.38, y, CONTROLLER_BOTTOM_Z - 0.85),
        (x + 0.38, y, MAIN_PCB_BOTTOM_Z + 0.95),
        (x + 0.72, y, MAIN_PCB_BOTTOM_Z + 0.72),
    ]
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(material)
    return obj


def create_conthrough(
    side: str,
    footprint: dict,
    collection: bpy.types.Collection,
    half_root: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    assembly = bpy.data.objects.new(f"{side}_Conthrough_Assembly", None)
    collection.objects.link(assembly)
    parent_local(assembly, half_root)
    assembly["conthrough_assembly"] = True
    assembly["conthrough_spec"] = "9 pin, 1.27 mm pitch, H=2.5 mm"
    assembly["conthrough_source"] = AUTO_KDK_SOURCE
    mark_generated(assembly, side, "assembly", "conthrough")

    for row_index, row in enumerate(footprint["rows"], 1):
        row_x = sum(item["center"][0] for item in row) / len(row)
        row_y = sum(item["center"][1] for item in row) / len(row)
        body = create_box(
            f"{side}_Conthrough_Row_{row_index}_Housing",
            (row_x, row_y, MAIN_PCB_BOTTOM_Z - CONTHROUGH_BODY_HEIGHT / 2),
            (CONTHROUGH_BODY_WIDTH, CONTHROUGH_BODY_LENGTH, CONTHROUGH_BODY_HEIGHT),
            collection,
            materials["black"],
            bevel=0.13,
        )
        parent_local(body, assembly)
        mark_generated(body, side, "housing", "conthrough")
        for pin_index, pad in enumerate(row, 1):
            wire = create_conthrough_wire_curve(
                f"{side}_Conthrough_Row_{row_index}_Pin_{pin_index:02d}",
                pad["center"][0],
                pad["center"][1],
                collection,
                materials["gold"],
            )
            parent_local(wire, assembly)
            wire["conthrough_row"] = row_index
            wire["conthrough_pin"] = pin_index
            wire["conthrough_pad_center_mm"] = list(pad["center"])
            mark_generated(wire, side, "spring_pin", "conthrough")
    return assembly


def capsule_outline(
    cx: float,
    cy: float,
    length: float,
    width: float,
    *,
    segments: int = 8,
) -> list[tuple[float, float]]:
    radius = width / 2
    half_straight = (length - width) / 2
    points = []
    for index in range(segments + 1):
        angle = math.pi / 2 + math.pi * index / segments
        points.append((cx - half_straight + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    for index in range(segments + 1):
        angle = -math.pi / 2 + math.pi * index / segments
        points.append((cx + half_straight + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def create_sensor_board_local(
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    outline = [
        (-SENSOR_WIDTH / 2, -SENSOR_LENGTH / 2),
        (SENSOR_WIDTH / 2, -SENSOR_LENGTH / 2),
        (SENSOR_WIDTH / 2, SENSOR_LENGTH / 2),
        (-SENSOR_WIDTH / 2, SENSOR_LENGTH / 2),
    ]
    board = create_prism(
        "Right_Mouse_Sensor_PCB",
        outline,
        -SENSOR_THICKNESS / 2,
        SENSOR_THICKNESS / 2,
        collection,
        material,
    )
    slot_centers = [(-2.55, -5.25), (2.55, -5.25), (-2.55, 5.25), (2.55, 5.25)]
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for cx, cy in slot_centers:
        add_prism_geometry(
            vertices,
            faces,
            capsule_outline(cx, cy, SENSOR_SLOT_LENGTH, SENSOR_SLOT_WIDTH),
            -1.1,
            1.1,
        )
    mesh = bpy.data.meshes.new("MouseSensor_Slot_Cutters_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cutter = bpy.data.objects.new("Right_Mouse_Sensor_Slot_Cutters", mesh)
    collection.objects.link(cutter)
    modifier = board.modifiers.new("Actual_Mounting_Slots", "BOOLEAN")
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
    board["actual_mounting_slots"] = 4
    return board


def local_component_box(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    *,
    bevel: float = 0.10,
) -> bpy.types.Object:
    return create_box(name, center, size, collection, material, bevel=bevel)


def create_fpc_ribbon(
    collection: bpy.types.Collection,
    materials: dict[str, bpy.types.Material],
    parent: bpy.types.Object,
    sensor_pose: Matrix,
) -> bpy.types.Object:
    connector_center = sensor_pose @ SENSOR_FPC_CONNECTOR_LOCAL
    points = [
        Vector((component_x("Right", 81.7), 33.5, CONTROLLER_BOTTOM_Z - 0.78)),
        Vector((component_x("Right", 81.7), 27.0, MAIN_PCB_BOTTOM_Z - 0.65)),
        Vector((-14.0, 14.0, MAIN_PCB_BOTTOM_Z - 0.45)),
        Vector((7.0, 2.0, MAIN_PCB_BOTTOM_Z - 0.45)),
        Vector((11.5, -13.0, MAIN_PCB_BOTTOM_Z - 0.25)),
        Vector((connector_center.x, -19.0, connector_center.z)),
        Vector((connector_center.x, SENSOR_FPC_GROOVE_Y, connector_center.z)),
        connector_center,
    ]
    vertices: list[tuple[float, float, float]] = []
    for index, point in enumerate(points):
        if index == 0:
            tangent = points[1] - points[0]
        elif index == len(points) - 1:
            tangent = points[-1] - points[-2]
        else:
            tangent = points[index + 1] - points[index - 1]
        normal = Vector((-tangent.y, tangent.x, 0.0))
        if normal.length < 1e-6:
            normal = Vector((1, 0, 0))
        normal.normalize()
        left = point + normal * FPC_WIDTH / 2
        right = point - normal * FPC_WIDTH / 2
        vertices.extend((tuple(left), tuple(right)))
    faces = []
    for index in range(len(points) - 1):
        base = index * 2
        faces.append((base, base + 2, base + 3, base + 1))
    mesh = bpy.data.meshes.new("SensorFPC_Ribbon_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(materials["fpc"])
    mesh.materials.append(materials["fpc_blue"])
    for index, polygon in enumerate(mesh.polygons):
        polygon.material_index = 1 if index in {0, len(mesh.polygons) - 1} else 0
    mesh.update()
    solidify = None
    obj = bpy.data.objects.new("Right_Mouse_Sensor_FPC_Ribbon", mesh)
    collection.objects.link(obj)
    solidify = obj.modifiers.new("FPC_Thickness", "SOLIDIFY")
    solidify.thickness = FPC_THICKNESS
    solidify.offset = 0
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    parent_local(obj, parent)
    obj["fpc_pitch_mm"] = FPC_PITCH
    obj["fpc_pin_count"] = FPC_PIN_COUNT
    obj["fpc_width_mm"] = FPC_WIDTH
    obj["case_escape_groove_mm"] = [connector_center.x, SENSOR_FPC_GROOVE_Y, connector_center.z]
    return mark_generated(obj, "Right", "fpc_ribbon", "mouse_sensor")


def mouse_sensor_pose() -> Matrix:
    rotation = Matrix.Rotation(math.radians(SENSOR_TANGENT_ANGLE_DEG), 4, "Y") @ Matrix.Rotation(
        math.radians(SENSOR_IN_PLANE_ANGLE_DEG), 4, "Z"
    )
    translation = SENSOR_LENS_TARGET - (rotation @ SENSOR_UPPER_LENS_LOCAL)
    return Matrix.Translation(translation) @ rotation


def create_mouse_sensor(
    collection: bpy.types.Collection,
    half_root: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    assembly = bpy.data.objects.new("Right_Mouse_Sensor_Assembly", None)
    collection.objects.link(assembly)
    parent_local(assembly, half_root)
    assembly["mouse_sensor_assembly"] = True
    assembly["mouse_sensor_model"] = "small-mouse-sensor-module"
    assembly["mouse_sensor_chip"] = "PAW3222"
    assembly["mouse_sensor_source"] = SENSOR_SOURCE
    assembly["mouse_sensor_dimensions_mm"] = [SENSOR_LENGTH, SENSOR_WIDTH, SENSOR_THICKNESS]
    assembly["mouse_sensor_pinout"] = "3.3V, CS, MOTION, SDIO, SCLK, GND"
    assembly["mouse_sensor_mount"] = "right top-case tangent pocket"
    assembly["mouse_sensor_lens_target_mm"] = list(SENSOR_LENS_TARGET)
    assembly["mouse_sensor_fpc_direction"] = "+Y toward Auto-KDK through adjacent groove"
    mark_generated(assembly, "Right", "assembly", "mouse_sensor")

    sensor_pose = mouse_sensor_pose()
    board = create_sensor_board_local(collection, materials["sensor_pcb"])
    board.matrix_world = sensor_pose
    parent_local(board, assembly)
    board["board_length_mm"] = SENSOR_LENGTH
    board["board_width_mm"] = SENSOR_WIDTH
    mark_generated(board, "Right", "pcb", "mouse_sensor")

    local_parts = [
        ("Optical_Sensor", (0, 1.2, 0.82), (4.6, 5.2, 0.64), "black", 0.15),
        ("Optical_Shield", (0, 1.2, 1.30), (5.6, 6.4, 0.50), "metal", 0.18),
        ("FPC_6P_Connector", tuple(SENSOR_FPC_CONNECTOR_LOCAL), (6.2, 2.5, 1.10), "white", 0.10),
        ("SMD_01", (-2.4, -1.4, 0.78), (1.5, 0.9, 0.55), "black", 0.05),
        ("SMD_02", (2.35, -1.4, 0.78), (1.3, 0.8, 0.50), "black", 0.05),
    ]
    for suffix, center, size, material, bevel in local_parts:
        part = local_component_box(
            f"Right_Mouse_Sensor_{suffix}", center, size, collection, materials[material], bevel=bevel
        )
        part.matrix_world = sensor_pose @ part.matrix_world
        parent_local(part, assembly)
        if suffix == "FPC_6P_Connector":
            part["connector_type"] = "0.5 mm pitch 6-pin FPC"
        mark_generated(part, "Right", suffix.lower(), "mouse_sensor")

    for suffix, local_center, radius, depth, material_name in (
        ("Upper_Lens", tuple(SENSOR_UPPER_LENS_LOCAL), 1.12, 0.55, "metal"),
        ("Lower_Lens", (0, 0.10, 1.68), 0.82, 0.42, "lens"),
    ):
        lens = add_cylinder(
            f"Right_Mouse_Sensor_{suffix}",
            local_center,
            radius,
            depth,
            collection,
            materials[material_name],
            vertices=32,
        )
        lens.matrix_world = sensor_pose @ lens.matrix_world
        parent_local(lens, assembly)
        mark_generated(lens, "Right", suffix.lower(), "mouse_sensor")

    create_fpc_ribbon(collection, materials, assembly, sensor_pose)
    return assembly


def setup_exploded_view(enabled: bool, spacing: float) -> dict:
    module_path = Path(__file__).with_name("setup_assembly_exploded_view.py")
    spec = importlib.util.spec_from_file_location("akdk_exploded_setup_controller", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.setup_exploded_view(enabled=enabled, spacing_mm=spacing)


def build_modules(*, save: bool = True, setup_exploded: bool = True) -> dict:
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    keyboard_collection = bpy.data.collections.get("Keyboard_Model")
    keyboard_root = bpy.data.objects.get("Keyboard_Root")
    if keyboard_collection is None or keyboard_root is None:
        raise RuntimeError("Keyboard_Model or Keyboard_Root is missing")
    collection = ensure_collection(COLLECTION_NAME, keyboard_collection)
    clean_generated(collection)

    materials = {
        # Keep the Auto-KDK board on the same dark-green solder mask as the
        # main switch PCB in every exported colorway.
        "controller_pcb": ensure_material(
            "AutoKDK_PCB_Green",
            MAIN_PCB_SOLDER_MASK_COLOR,
            roughness=MAIN_PCB_SOLDER_MASK_ROUGHNESS,
        ),
        "sensor_pcb": ensure_material("MouseSensor_PCB_Green", (0.018, 0.34, 0.17, 1), roughness=0.34),
        "dark_pcb": ensure_material("Controller_Module_PCB", (0.018, 0.035, 0.030, 1), roughness=0.40),
        "pad": ensure_material("Controller_Gold_Pads", (0.78, 0.47, 0.08, 1), roughness=0.24, metallic=0.78),
        "gold": ensure_material("Conthrough_Gold_Alloy", (0.86, 0.51, 0.12, 1), roughness=0.20, metallic=0.88),
        "metal": ensure_material("Controller_Shield_Metal", (0.60, 0.63, 0.65, 1), roughness=0.30, metallic=0.82),
        "black": ensure_material("Controller_Component_Black", (0.010, 0.014, 0.018, 1), roughness=0.38),
        "usb_cavity": ensure_material("USB_C_Cavity_Black", (0.002, 0.003, 0.004, 1), roughness=0.32),
        "usb_tongue": ensure_material("USB_C_Tongue_Dark", (0.018, 0.022, 0.026, 1), roughness=0.42),
        "usb_contact": ensure_material("USB_C_Contact_Copper", (0.42, 0.25, 0.065, 1), roughness=0.34, metallic=0.62),
        "white": ensure_material("Connector_White", (0.86, 0.84, 0.75, 1), roughness=0.52),
        "battery": ensure_material("LiPo_Silver_Pouch", (0.55, 0.58, 0.61, 1), roughness=0.42, metallic=0.55),
        "label": ensure_material("LiPo_Label_Black", (0.015, 0.018, 0.020, 1), roughness=0.62),
        "red": ensure_material("Battery_Wire_Red", (0.52, 0.015, 0.018, 1), roughness=0.42),
        "lens": ensure_material("MouseSensor_Lens", (0.06, 0.08, 0.07, 1), roughness=0.16, metallic=0.12),
        "fpc": ensure_material("Sensor_FPC_White", (0.89, 0.87, 0.72, 1), roughness=0.46),
        "fpc_blue": ensure_material("Sensor_FPC_Blue_End", (0.035, 0.20, 0.56, 1), roughness=0.40),
    }

    summaries = {}
    for side in ("Left", "Right"):
        half_root = bpy.data.objects.get(f"{side}_Half_Root")
        if half_root is None:
            raise RuntimeError(f"Missing {side}_Half_Root")
        footprint = controller_footprint(side)
        create_conthrough(side, footprint, collection, half_root, materials)
        create_controller(side, footprint, collection, half_root, materials)
        summaries[side] = {
            "package": footprint["package"],
            "conthrough_pins": len(footprint["pads"]),
            "pin_pitch_mm": footprint["pitch"],
            "row_separation_mm": footprint["row_separation"],
        }

    right_root = bpy.data.objects.get("Right_Half_Root")
    create_mouse_sensor(collection, right_root, materials)

    keyboard_root["controller_model_revision"] = REVISION
    keyboard_root["controller_model_source"] = AUTO_KDK_SOURCE
    keyboard_root["controller_dimensions_mm"] = [CONTROLLER_LENGTH, CONTROLLER_WIDTH, CONTROLLER_THICKNESS]
    keyboard_root["controller_keep_out_dimensions_mm"] = [
        CONTROLLER_LENGTH,
        CONTROLLER_KEEP_OUT_WIDTH,
        CONTROLLER_THICKNESS,
    ]
    keyboard_root["conthrough_spec"] = "2 rows/controller; 9 pin; 1.27 mm pitch; row separation 19 mm; H=2.5 mm"
    keyboard_root["mouse_sensor_model_source"] = SENSOR_SOURCE
    keyboard_root["mouse_sensor_dimensions_mm"] = [SENSOR_LENGTH, SENSOR_WIDTH, SENSOR_THICKNESS]
    keyboard_root["mouse_sensor_fpc"] = "0.5 mm pitch, 6 pin"

    exploded_summary = None
    if setup_exploded:
        enabled = bool(keyboard_root.get("exploded_view_enabled", True))
        spacing = float(keyboard_root.get("exploded_view_spacing_mm", 30.0))
        exploded_summary = setup_exploded_view(enabled=enabled, spacing=spacing)
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    return {
        "revision": REVISION,
        "controller_source": AUTO_KDK_SOURCE,
        "sensor_source": SENSOR_SOURCE,
        "controller_dimensions_mm": [CONTROLLER_LENGTH, CONTROLLER_WIDTH, CONTROLLER_THICKNESS],
        "controller_keep_out_dimensions_mm": [
            CONTROLLER_LENGTH,
            CONTROLLER_KEEP_OUT_WIDTH,
            CONTROLLER_THICKNESS,
        ],
        "sensor_dimensions_mm": [SENSOR_LENGTH, SENSOR_WIDTH, SENSOR_THICKNESS],
        "usb_c_receptacle": {
            "shell_opening_mm": [USB_C_SHELL_OPENING_WIDTH, USB_C_SHELL_OPENING_HEIGHT],
            "shell_length_mm": 6.20,
            "contact_count": USB_C_CONTACT_COUNT_PER_SIDE * 2,
            "contact_pitch_mm": USB_C_CONTACT_PITCH,
        },
        "fpc": {"pins": FPC_PIN_COUNT, "pitch_mm": FPC_PITCH, "width_mm": FPC_WIDTH},
        "sides": summaries,
        "exploded_view": exploded_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--no-exploded", action="store_true")
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    print(
        "CONTROLLER_SENSOR_BUILD_RESULT="
        + json.dumps(
            build_modules(save=not args.no_save, setup_exploded=not args.no_exploded),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
