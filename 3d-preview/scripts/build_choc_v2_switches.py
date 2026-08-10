"""Build exploded-view-ready Kailh Choc V2 (PG1353) switch assemblies.

The script upgrades the existing AKDK preview switches in-place while preserving
their transforms and keycap alignment. Geometry is shared between instances;
individual parts remain separate objects so a future exploded-view controller
can move them using the ``explode_vector_mm`` custom property.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import bpy
from mathutils import Matrix


REVISION = 9
SWITCH_ORIENTATION_Z_DEG = 90.0
MX_CROSS_POST_LENGTH_MM = 4.00
MX_CROSS_POST_WIDTH_MM = 1.30
MX_CROSS_POST_TOP_LOCAL_Z = 1.45
MX_CROSS_POST_BOTTOM_LOCAL_Z = -3.30
STEM_INTERFACE_DIAMETER_MM = 5.50
STEM_COLLAR_INNER_DIAMETER_MM = 4.60
COVER_STEM_OPENING_DIAMETER_MM = 6.50
STEM_INTERFACE_BOTTOM_LOCAL_Z = -1.75
STEM_INTERFACE_TOP_LOCAL_Z = 1.55
STEM_INTERNAL_BODY_TOP_LOCAL_Z = -3.10
STEM_ASSEMBLY_Z = 3.30
HOUSING_TOP_Z = 1.55
COVER_BOTTOM_Z = -1.55
HOUSING_BOTTOM_Z = -3.75
ELECTRICAL_PIN_BOTTOM_Z = HOUSING_BOTTOM_Z - 2.20
REFERENCE_PRODUCT = (
    ".tmp/keyboard-model/reference/switch/"
    "20200415135137bb8f5681892c4a38b227e8e03cf814f6.webp"
)
REFERENCE_DRAWING = (
    ".tmp/keyboard-model/reference/switch/"
    "202004151351066711915064c54f7d9dba66f572e3baff.webp"
)
REFERENCE_VARIANTS = (
    ".tmp/keyboard-model/reference/switch/"
    "202004151401582f9af6e3a790403e860a460626ea6343.webp"
)


def srgb_channel_to_linear(value: float) -> float:
    value = max(0.0, min(1.0, value))
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def srgb_hex_to_linear(hex_color: str) -> tuple[float, float, float, float]:
    value = hex_color.lstrip("#")
    rgb = [int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]
    return tuple(srgb_channel_to_linear(channel) for channel in rgb) + (1.0,)


def ensure_material(
    name: str,
    hex_color: str,
    *,
    metallic: float = 0.0,
    roughness: float = 0.4,
    alpha: float = 1.0,
    transmission: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    color = srgb_hex_to_linear(hex_color)
    color = (color[0], color[1], color[2], alpha)
    material.diffuse_color = color
    nodes = material.node_tree.nodes
    output = next((node for node in nodes if node.type == "OUTPUT_MATERIAL"), None)
    principled = None
    if output is not None and output.inputs["Surface"].is_linked:
        linked_node = output.inputs["Surface"].links[0].from_node
        if linked_node.type == "BSDF_PRINCIPLED":
            principled = linked_node
    if principled is None:
        principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        if output is None:
            output = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    # Remove stale unlinked Principled nodes produced by older revisions.
    for node in list(nodes):
        if node.type == "BSDF_PRINCIPLED" and node != principled and not node.outputs["BSDF"].is_linked:
            nodes.remove(node)
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    if "Metallic IOR Level" in principled.inputs:
        principled.inputs["Metallic IOR Level"].default_value = metallic
    elif "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = metallic
    if "Alpha" in principled.inputs:
        principled.inputs["Alpha"].default_value = alpha
    if "Transmission Weight" in principled.inputs:
        principled.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in principled.inputs:
        principled.inputs["Transmission"].default_value = transmission
    if alpha < 1.0:
        try:
            material.surface_render_method = "DITHERED"
        except (AttributeError, TypeError):
            pass
        material.use_transparency_overlap = False
    return material


class MeshBuilder:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []

    def add_box(
        self,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
    ) -> None:
        cx, cy, cz = center
        sx, sy, sz = (axis / 2.0 for axis in size)
        base = len(self.vertices)
        self.vertices.extend(
            [
                (cx - sx, cy - sy, cz - sz),
                (cx + sx, cy - sy, cz - sz),
                (cx + sx, cy + sy, cz - sz),
                (cx - sx, cy + sy, cz - sz),
                (cx - sx, cy - sy, cz + sz),
                (cx + sx, cy - sy, cz + sz),
                (cx + sx, cy + sy, cz + sz),
                (cx - sx, cy + sy, cz + sz),
            ]
        )
        self.faces.extend(
            [
                (base + 3, base + 2, base + 1, base + 0),
                (base + 4, base + 5, base + 6, base + 7),
                (base + 0, base + 1, base + 5, base + 4),
                (base + 1, base + 2, base + 6, base + 5),
                (base + 2, base + 3, base + 7, base + 6),
                (base + 3, base + 0, base + 4, base + 7),
            ]
        )

    def add_cylinder(
        self,
        center: tuple[float, float, float],
        radius: float,
        depth: float,
        *,
        segments: int = 32,
    ) -> None:
        cx, cy, cz = center
        bottom = cz - depth / 2.0
        top = cz + depth / 2.0
        base = len(self.vertices)
        for z in (bottom, top):
            for index in range(segments):
                angle = math.tau * index / segments
                self.vertices.append(
                    (cx + radius * math.cos(angle), cy + radius * math.sin(angle), z)
                )
        for index in range(segments):
            nxt = (index + 1) % segments
            self.faces.append((base + index, base + nxt, base + segments + nxt, base + segments + index))
        self.faces.append(tuple(base + index for index in reversed(range(segments))))
        self.faces.append(tuple(base + segments + index for index in range(segments)))

    def add_annulus(
        self,
        center: tuple[float, float, float],
        outer_radius: float,
        inner_radius: float,
        depth: float,
        *,
        segments: int = 32,
    ) -> None:
        cx, cy, cz = center
        z_values = (cz - depth / 2.0, cz + depth / 2.0)
        base = len(self.vertices)
        for z in z_values:
            for radius in (outer_radius, inner_radius):
                for index in range(segments):
                    angle = math.tau * index / segments
                    self.vertices.append(
                        (cx + radius * math.cos(angle), cy + radius * math.sin(angle), z)
                    )
        outer_bottom = base
        inner_bottom = base + segments
        outer_top = base + segments * 2
        inner_top = base + segments * 3
        for index in range(segments):
            nxt = (index + 1) % segments
            self.faces.extend(
                [
                    (outer_bottom + index, outer_bottom + nxt, outer_top + nxt, outer_top + index),
                    (inner_bottom + nxt, inner_bottom + index, inner_top + index, inner_top + nxt),
                    (outer_top + index, outer_top + nxt, inner_top + nxt, inner_top + index),
                    (outer_bottom + nxt, outer_bottom + index, inner_bottom + index, inner_bottom + nxt),
                ]
            )

    def add_rectangular_plate_with_circular_hole(
        self,
        center: tuple[float, float, float],
        size_x: float,
        size_y: float,
        hole_radius: float,
        depth: float,
        *,
        segments: int = 64,
    ) -> None:
        """Add a closed rectangular plate whose only opening is a circle."""
        cx, cy, cz = center
        half_x = size_x / 2.0
        half_y = size_y / 2.0
        z_values = (cz - depth / 2.0, cz + depth / 2.0)
        base = len(self.vertices)

        for z in z_values:
            for radius_kind in ("outer", "inner"):
                for index in range(segments):
                    angle = math.tau * index / segments
                    direction_x = math.cos(angle)
                    direction_y = math.sin(angle)
                    if radius_kind == "outer":
                        scale_x = half_x / abs(direction_x) if abs(direction_x) > 1e-9 else float("inf")
                        scale_y = half_y / abs(direction_y) if abs(direction_y) > 1e-9 else float("inf")
                        radius = min(scale_x, scale_y)
                    else:
                        radius = hole_radius
                    self.vertices.append(
                        (cx + radius * direction_x, cy + radius * direction_y, z)
                    )

        outer_bottom = base
        inner_bottom = base + segments
        outer_top = base + segments * 2
        inner_top = base + segments * 3
        for index in range(segments):
            nxt = (index + 1) % segments
            self.faces.extend(
                [
                    (outer_bottom + index, outer_bottom + nxt, outer_top + nxt, outer_top + index),
                    (inner_bottom + nxt, inner_bottom + index, inner_top + index, inner_top + nxt),
                    (outer_top + index, outer_top + nxt, inner_top + nxt, inner_top + index),
                    (outer_bottom + nxt, outer_bottom + index, inner_bottom + index, inner_bottom + nxt),
                ]
            )

    @staticmethod
    def rounded_points(
        size_x: float,
        size_y: float,
        radius: float,
        segments_per_corner: int,
    ) -> list[tuple[float, float]]:
        half_x = size_x / 2.0
        half_y = size_y / 2.0
        radius = min(radius, half_x, half_y)
        corners = [
            (half_x - radius, half_y - radius, 0.0),
            (-half_x + radius, half_y - radius, math.pi / 2.0),
            (-half_x + radius, -half_y + radius, math.pi),
            (half_x - radius, -half_y + radius, math.pi * 1.5),
        ]
        points: list[tuple[float, float]] = []
        for center_x, center_y, start in corners:
            for step in range(segments_per_corner + 1):
                angle = start + (math.pi / 2.0) * step / segments_per_corner
                points.append(
                    (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
                )
        return points

    def add_rounded_prism(
        self,
        layers: list[tuple[float, float, float, float]],
        *,
        segments_per_corner: int = 4,
        cap_bottom: bool = True,
        cap_top: bool = True,
    ) -> None:
        rings: list[list[int]] = []
        for z, size_x, size_y, radius in layers:
            ring = []
            for x, y in self.rounded_points(size_x, size_y, radius, segments_per_corner):
                ring.append(len(self.vertices))
                self.vertices.append((x, y, z))
            rings.append(ring)
        count = len(rings[0])
        for lower, upper in zip(rings, rings[1:]):
            for index in range(count):
                nxt = (index + 1) % count
                self.faces.append((lower[index], lower[nxt], upper[nxt], upper[index]))
        if cap_bottom:
            self.faces.append(tuple(reversed(rings[0])))
        if cap_top:
            self.faces.append(tuple(rings[-1]))

    def add_rounded_shell(
        self,
        size_x: float,
        size_y: float,
        z_bottom: float,
        z_top: float,
        radius: float,
        wall: float,
        *,
        segments_per_corner: int = 4,
    ) -> None:
        outer = self.rounded_points(size_x, size_y, radius, segments_per_corner)
        inner = self.rounded_points(
            size_x - wall * 2.0,
            size_y - wall * 2.0,
            max(0.1, radius - wall),
            segments_per_corner,
        )
        base = len(self.vertices)
        for z in (z_bottom, z_top):
            self.vertices.extend((x, y, z) for x, y in outer)
            self.vertices.extend((x, y, z) for x, y in inner)
        count = len(outer)
        outer_bottom = base
        inner_bottom = base + count
        outer_top = base + count * 2
        inner_top = base + count * 3
        for index in range(count):
            nxt = (index + 1) % count
            self.faces.extend(
                [
                    (outer_bottom + index, outer_bottom + nxt, outer_top + nxt, outer_top + index),
                    (inner_bottom + nxt, inner_bottom + index, inner_top + index, inner_top + nxt),
                    (outer_top + index, outer_top + nxt, inner_top + nxt, inner_top + index),
                    (outer_bottom + nxt, outer_bottom + index, inner_bottom + index, inner_bottom + nxt),
                ]
            )

    def add_cross_prism(self, arm_length: float, arm_width: float, depth: float) -> None:
        half_length = arm_length / 2.0
        half_width = arm_width / 2.0
        outline = [
            (-half_width, -half_length),
            (half_width, -half_length),
            (half_width, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (half_width, half_width),
            (half_width, half_length),
            (-half_width, half_length),
            (-half_width, half_width),
            (-half_length, half_width),
            (-half_length, -half_width),
            (-half_width, -half_width),
        ]
        base = len(self.vertices)
        for z in (-depth / 2.0, depth / 2.0):
            self.vertices.extend((x, y, z) for x, y in outline)
        count = len(outline)
        for index in range(count):
            nxt = (index + 1) % count
            self.faces.append((base + index, base + nxt, base + count + nxt, base + count + index))
        self.faces.append(tuple(base + index for index in reversed(range(count))))
        self.faces.append(tuple(base + count + index for index in range(count)))

    def to_mesh(self, name: str) -> bpy.types.Mesh:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update(calc_edges=True)
        return mesh


def create_cover_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_rounded_shell(15.0, 15.0, -1.55, 1.22, 1.25, 0.65)
    # A single top plate eliminates the legacy square corner gaps.  The only
    # opening is the drawing-specified circular clearance around the stem.
    builder.add_rectangular_plate_with_circular_hole(
        (0.0, 0.0, 1.38),
        13.7,
        13.7,
        COVER_STEM_OPENING_DIAMETER_MM / 2.0,
        0.34,
        segments=64,
    )
    # Cover retaining clips visible on all four sides.
    builder.add_box((0.0, -7.175, -0.75), (3.0, 0.65, 1.60))
    builder.add_box((0.0, 7.175, -0.75), (3.0, 0.65, 1.60))
    builder.add_box((-7.175, 0.0, -0.75), (0.65, 3.0, 1.60))
    builder.add_box((7.175, 0.0, -0.75), (0.65, 3.0, 1.60))
    return builder.to_mesh("AKDK_ChocV2_Cover_PG1353_Mesh")


def create_base_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_rounded_prism(
        [
            (-1.10, 13.45, 13.45, 0.95),
            (-0.88, 13.95, 13.95, 1.15),
            (0.88, 13.95, 13.95, 1.15),
            (1.10, 13.55, 13.55, 0.98),
        ]
    )
    # Central PCB boss (drawing: approximately 4.80 mm diameter, 1.65 mm long).
    builder.add_cylinder((0.0, 0.0, -1.925), 2.40, 1.65, segments=32)
    # One asymmetric locating pin from the recommended PCB footprint.
    builder.add_cylinder((-5.15, -5.0, -2.60), 0.80, 3.00, segments=20)
    # Side latch shoulders.
    builder.add_box((-6.625, 0.0, 0.15), (0.7, 3.8, 1.25))
    builder.add_box((6.625, 0.0, 0.15), (0.7, 3.8, 1.25))
    return builder.to_mesh("AKDK_ChocV2_Base_PG1353_Mesh")


def create_stem_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    # Choc V2 uses a positive MX cross inside a circular collar.  The volume
    # between the cross post and the collar is intentionally empty.
    builder.add_annulus(
        (
            0.0,
            0.0,
            (STEM_INTERFACE_TOP_LOCAL_Z + STEM_INTERFACE_BOTTOM_LOCAL_Z) / 2.0,
        ),
        STEM_INTERFACE_DIAMETER_MM / 2.0,
        STEM_COLLAR_INNER_DIAMETER_MM / 2.0,
        STEM_INTERFACE_TOP_LOCAL_Z - STEM_INTERFACE_BOTTOM_LOCAL_Z,
        segments=40,
    )
    cross_start = len(builder.vertices)
    cross_depth = MX_CROSS_POST_TOP_LOCAL_Z - MX_CROSS_POST_BOTTOM_LOCAL_Z
    cross_center_z = (MX_CROSS_POST_TOP_LOCAL_Z + MX_CROSS_POST_BOTTOM_LOCAL_Z) / 2.0
    builder.add_cross_prism(
        MX_CROSS_POST_LENGTH_MM,
        MX_CROSS_POST_WIDTH_MM,
        cross_depth,
    )
    for vertex_index in range(cross_start, len(builder.vertices)):
        x, y, z = builder.vertices[vertex_index]
        builder.vertices[vertex_index] = (x, y, z + cross_center_z)

    # The guide body remains well below the transparent cover top.  It overlaps
    # the cross post below the collar so the post is structurally connected,
    # without reading as a shallow coloured floor inside the MX interface.
    builder.add_rounded_prism(
        [(-4.35, 4.9, 4.9, 0.55), (STEM_INTERNAL_BODY_TOP_LOCAL_Z, 5.5, 5.3, 0.62)],
        segments_per_corner=3,
    )
    builder.add_box((-3.0, 0.0, -3.65), (1.1, 2.2, 1.00))
    builder.add_box((3.0, 0.0, -3.65), (1.1, 2.2, 1.00))
    builder.add_box((0.0, -3.0, -3.65), (2.2, 1.1, 1.00))
    builder.add_box((0.0, 3.0, -3.65), (2.2, 1.1, 1.00))
    builder.add_cylinder((0.0, 0.0, -5.05), 1.05, 2.0, segments=24)

    mesh = builder.to_mesh("AKDK_ChocV2_Stem_PG1353_Mesh")
    # Smooth the collar walls while keeping the cross faces crisp.
    for polygon in mesh.polygons:
        radial_distance = math.hypot(polygon.center.x, polygon.center.y)
        polygon.use_smooth = abs(polygon.normal.z) < 0.25 and radial_distance > 2.15
    return mesh


def create_fix_pin_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_box((0.0, 0.0, 0.0), (0.42, 3.0, 2.25))
    builder.add_box((0.55, 0.0, 0.75), (1.1, 0.55, 0.45))
    return builder.to_mesh("AKDK_ChocV2_Fix_Pin_Mesh")


def create_fixed_contact_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_box((0.0, -4.2, 0.45), (0.42, 3.7, 2.8))
    # With the object placed at Z=-1.15, this reaches 2.20 mm below the
    # housing datum in the dimension drawing while continuing into the case.
    builder.add_cylinder((0.0, 0.0, -2.65), 0.60, 4.30, segments=18)
    builder.add_box((-0.45, -4.2, 1.65), (1.3, 1.15, 0.42))
    return builder.to_mesh("AKDK_ChocV2_Fixed_Contact_Mesh")


def create_moving_contact_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_box((0.0, 0.0, 0.35), (0.35, 3.4, 2.65))
    # The moving-contact object is 0.20 mm higher than the fixed contact, so
    # its pin is correspondingly longer to share the same terminal-tip datum.
    builder.add_cylinder((0.0, 0.0, -2.75), 0.60, 4.50, segments=18)
    builder.add_box((-0.55, 0.0, 1.45), (1.45, 0.95, 0.32))
    return builder.to_mesh("AKDK_ChocV2_Moving_Contact_Mesh")


def create_push_rod_mesh() -> bpy.types.Mesh:
    builder = MeshBuilder()
    builder.add_box((0.0, 0.0, 0.0), (1.15, 2.05, 2.2))
    builder.add_cylinder((0.0, 0.0, -1.45), 0.38, 1.45, segments=16)
    return builder.to_mesh("AKDK_ChocV2_Push_Rod_Mesh")


def create_curve_data(
    name: str,
    points: list[tuple[float, float, float]],
    bevel_depth: float,
) -> bpy.types.Curve:
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (*coordinates, 1.0)
    return curve


def create_coil_spring_curve() -> bpy.types.Curve:
    points = []
    count = 96
    turns = 7.0
    for index in range(count):
        factor = index / (count - 1)
        angle = math.tau * turns * factor
        radius = 1.62
        points.append((radius * math.cos(angle), radius * math.sin(angle), -1.35 + 2.7 * factor))
    return create_curve_data("AKDK_ChocV2_Coil_Spring_Curve", points, 0.16)


def create_torsion_spring_curve() -> bpy.types.Curve:
    points = [(-1.8, -0.55, 0.0)]
    turns = 2.0
    for index in range(40):
        factor = index / 39.0
        angle = math.tau * turns * factor
        points.append((-0.8 + 0.62 * math.cos(angle), 0.62 * math.sin(angle), 0.15 * factor))
    points.extend([(0.4, 0.85, 0.35), (1.6, 1.2, 0.45)])
    return create_curve_data("AKDK_ChocV2_Torsion_Spring_Curve", points, 0.13)


def create_click_bar_curve() -> bpy.types.Curve:
    points = [(-4.8, -3.8, 0.0), (-5.2, -2.8, 0.2), (-5.2, 2.8, 0.2), (-4.8, 3.8, 0.0)]
    return create_curve_data("AKDK_ChocV2_Click_Bar_Curve", points, 0.22)


def assign_data_material(data: bpy.types.ID, material: bpy.types.Material) -> None:
    if hasattr(data, "materials"):
        data.materials.clear()
        data.materials.append(material)


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(collection)
        else:
            parent.children.link(collection)
    return collection


def link_object(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def create_object(
    name: str,
    data: bpy.types.ID | None,
    collection: bpy.types.Collection,
    parent: bpy.types.Object | None,
    location: tuple[float, float, float],
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, data)
    link_object(obj, collection)
    obj.parent = parent
    obj.location = location
    return obj


def tag_component(
    obj: bpy.types.Object,
    *,
    part: str,
    order: int,
    explode_vector: tuple[float, float, float],
) -> None:
    obj["choc_v2_part"] = part
    obj["explode_order"] = order
    obj["explode_vector_mm"] = explode_vector
    obj["assembled_location"] = tuple(obj.location)
    obj["generated_by"] = "build_choc_v2_switches.py"
    obj["choc_v2_revision"] = REVISION


@dataclass
class SwitchPlacement:
    name: str
    parent: bpy.types.Object
    matrix_local: Matrix
    collections: list[str]
    module_id: str
    properties: dict[str, object]
    keycap_name: str
    keycap_profile: str


def find_keycap(root: bpy.types.Object) -> bpy.types.Object:
    side = root.name.split("_", 1)[0]
    module_id = root.get("module_id")
    for obj in bpy.data.objects:
        if obj.name.startswith(f"{side}_Keycap_") and obj.get("module_id") == module_id:
            return obj
    raise RuntimeError(f"No keycap found for {root.name} / {module_id}")


def capture_switch_placements() -> list[SwitchPlacement]:
    pattern = re.compile(r"^(Left|Right)_Switch_\d{2}$")
    roots = [
        obj
        for obj in bpy.data.objects
        if pattern.match(obj.name) and obj.get("module_id") is not None
    ]
    placements: list[SwitchPlacement] = []
    preserved_property_names = {
        "module_id",
        "plate_surface_z_mm",
        "housing_bottom_z_mm",
        "housing_top_z_mm",
    }
    for root in sorted(roots, key=lambda item: item.name):
        if root.parent is None:
            raise RuntimeError(f"Switch root {root.name} has no half-root parent")
        keycap = find_keycap(root)
        # Rebuilds are idempotent: remove the orientation previously added by
        # this generator before applying the canonical orientation again.
        placement_matrix = root.matrix_local.copy()
        existing_orientation = float(root.get("switch_orientation_z_deg", 0.0))
        if abs(existing_orientation) > 1.0e-9:
            placement_matrix = placement_matrix @ Matrix.Rotation(
                math.radians(-existing_orientation), 4, "Z"
            )
        placements.append(
            SwitchPlacement(
                name=root.name,
                parent=root.parent,
                matrix_local=placement_matrix,
                collections=[collection.name for collection in root.users_collection],
                module_id=str(root["module_id"]),
                # Keep only scalar source-placement values. Blender IDPropertyArray
                # values become invalid when their owner is removed during an
                # idempotent rebuild and can crash Blender if assigned afterward.
                properties={
                    key: root[key]
                    for key in preserved_property_names
                    if key in root
                },
                keycap_name=keycap.name,
                keycap_profile=str(keycap.get("profile", "standard")),
            )
        )
    if len(placements) != 45:
        raise RuntimeError(f"Expected 45 Choc V2 switch placements, found {len(placements)}")
    return placements


def remove_existing_switch_roots(placements: list[SwitchPlacement]) -> None:
    for placement in placements:
        root = bpy.data.objects.get(placement.name)
        if root is None:
            continue
        descendants = list(root.children_recursive)
        for child in reversed(descendants):
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(root, do_unlink=True)


def remove_orphaned_generated_data() -> None:
    for datablocks in (bpy.data.meshes, bpy.data.curves):
        for data in list(datablocks):
            if data.name.startswith("AKDK_ChocV2_") and data.users == 0:
                datablocks.remove(data)
    for legacy_name in (
        "Choc_V2_Switch_Top_Housing_Mesh",
        "Choc_V2_Switch_Base_Mesh",
        "Choc_V2_Stem_Mesh",
    ):
        mesh = bpy.data.meshes.get(legacy_name)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for legacy_material_name in (
        "ChocV2_Stem_Socket_Shadow",
        "ChocV2_Stem_Socket_Interior",
    ):
        material = bpy.data.materials.get(legacy_material_name)
        if material is not None and material.users == 0:
            bpy.data.materials.remove(material)


def add_material_override(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if not obj.data.materials:
        obj.data.materials.append(material)
    slot = obj.material_slots[0]
    slot.link = "OBJECT"
    slot.material = material


def build() -> dict[str, object]:
    placements = capture_switch_placements()
    remove_existing_switch_roots(placements)
    remove_orphaned_generated_data()

    keyboard_model = bpy.data.collections.get("Keyboard_Model")
    parts_collection = ensure_collection("02b_Switch_Parts", keyboard_model)
    switch_collection = ensure_collection("02_Switches", keyboard_model)

    materials = {
        "cover": ensure_material(
            "ChocV2_Clear_Polycarbonate", "#DDE8EE", roughness=0.18, alpha=0.34, transmission=0.55
        ),
        "base": ensure_material("ChocV2_Base_Black_POM", "#101318", roughness=0.42),
        "stem_blue": ensure_material("ChocV2_Stem_Blue", "#009AC4", roughness=0.30),
        "stem_brown": ensure_material("ChocV2_Stem_Brown", "#A74D12", roughness=0.32),
        "spring": ensure_material("ChocV2_Spring_Steel", "#C9D0D8", metallic=0.92, roughness=0.22),
        "copper": ensure_material("ChocV2_Contact_Copper", "#B96D2D", metallic=0.78, roughness=0.24),
        "gold": ensure_material("ChocV2_Pin_Gold", "#D79727", metallic=0.72, roughness=0.25),
        "push_rod": ensure_material("ChocV2_Push_Rod_Green", "#2D7A39", roughness=0.40),
    }

    data = {
        "cover": create_cover_mesh(),
        "base": create_base_mesh(),
        "stem": create_stem_mesh(),
        "spring": create_coil_spring_curve(),
        "torsion_spring": create_torsion_spring_curve(),
        "click_bar": create_click_bar_curve(),
        "fix_pin": create_fix_pin_mesh(),
        "fixed_contact": create_fixed_contact_mesh(),
        "moving_contact": create_moving_contact_mesh(),
        "push_rod": create_push_rod_mesh(),
    }
    assign_data_material(data["cover"], materials["cover"])
    assign_data_material(data["base"], materials["base"])
    assign_data_material(data["stem"], materials["stem_brown"])
    assign_data_material(data["spring"], materials["spring"])
    assign_data_material(data["torsion_spring"], materials["spring"])
    assign_data_material(data["click_bar"], materials["spring"])
    assign_data_material(data["fix_pin"], materials["copper"])
    assign_data_material(data["fixed_contact"], materials["gold"])
    assign_data_material(data["moving_contact"], materials["copper"])
    assign_data_material(data["push_rod"], materials["push_rod"])

    blue_count = 0
    brown_count = 0
    part_count = 0
    for placement in placements:
        assembly = create_object(placement.name, None, switch_collection, placement.parent, (0.0, 0.0, 0.0))
        # In the source layout the torsion spring sits on local -X (left).
        # Rotate the complete switch +90 degrees so it sits on local -Y, the
        # keyboard-front side, without changing the switch centre or keycap.
        assembly.matrix_local = placement.matrix_local @ Matrix.Rotation(
            math.radians(SWITCH_ORIENTATION_Z_DEG), 4, "Z"
        )
        for key, value in placement.properties.items():
            if key not in {"choc_v2_revision", "generated_by"}:
                assembly[key] = value
        variant = "blue" if placement.keycap_profile == "low-profile-thumb" else "brown"
        blue_count += variant == "blue"
        brown_count += variant == "brown"
        assembly["switch_type"] = "Kailh Choc V2 (PG1353)"
        assembly["manufacturer"] = "Kailh"
        assembly["model"] = "PG1353 / Choc V2"
        assembly["module_id"] = placement.module_id
        assembly["connected_keycap"] = placement.keycap_name
        assembly["keycap_profile"] = placement.keycap_profile
        assembly["stem_variant"] = variant
        assembly["exploded_ready"] = True
        assembly["switch_orientation_z_deg"] = SWITCH_ORIENTATION_Z_DEG
        assembly["torsion_spring_side"] = "front (-Y)"
        assembly["choc_v2_revision"] = REVISION
        assembly["generated_by"] = "build_choc_v2_switches.py"
        assembly["reference_product"] = REFERENCE_PRODUCT
        assembly["reference_drawing"] = REFERENCE_DRAWING
        assembly["reference_variants"] = REFERENCE_VARIANTS
        assembly["housing_outer_mm"] = (15.0, 15.0, 5.30)
        assembly["stem_diameter_mm"] = STEM_INTERFACE_DIAMETER_MM
        assembly["cover_stem_opening_diameter_mm"] = COVER_STEM_OPENING_DIAMETER_MM
        assembly["cover_stem_radial_clearance_mm"] = (
            COVER_STEM_OPENING_DIAMETER_MM - STEM_INTERFACE_DIAMETER_MM
        ) / 2.0
        assembly["cover_stem_opening_shape"] = "circular_only"
        assembly["mx_cross_post_length_mm"] = MX_CROSS_POST_LENGTH_MM
        assembly["mx_cross_post_width_mm"] = MX_CROSS_POST_WIDTH_MM
        assembly["mx_cross_post_actual_geometry"] = True
        assembly["stem_collar_inner_diameter_mm"] = STEM_COLLAR_INNER_DIAMETER_MM
        assembly["stem_cross_post_top_inset_mm"] = (
            STEM_INTERFACE_TOP_LOCAL_Z - MX_CROSS_POST_TOP_LOCAL_Z
        )
        assembly["stem_cross_to_collar_space"] = "open"
        assembly["exposed_stem_geometry"] = "cylindrical_interface_only"
        assembly["stem_internal_body_top_local_z_mm"] = STEM_INTERNAL_BODY_TOP_LOCAL_Z
        assembly["stem_assembly_z_mm"] = STEM_ASSEMBLY_Z
        assembly["stem_collar_seat_offset_mm"] = (
            STEM_ASSEMBLY_Z + STEM_INTERFACE_BOTTOM_LOCAL_Z - HOUSING_TOP_Z
        )
        assembly["stem_exposed_above_cover_mm"] = (
            STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - HOUSING_TOP_Z
        )
        assembly["drawing_6_40_height_mm"] = (
            STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - COVER_BOTTOM_Z
        )
        assembly["external_height_excluding_pins_mm"] = (
            STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - HOUSING_BOTTOM_Z
        )
        assembly["electrical_pin_protrusion_mm"] = (
            HOUSING_BOTTOM_Z - ELECTRICAL_PIN_BOTTOM_Z
        )

        cover = create_object(f"{placement.name}_Cover", data["cover"], parts_collection, assembly, (0.0, 0.0, 0.0))
        tag_component(cover, part="cover", order=80, explode_vector=(0.0, 0.0, 8.0))

        stem = create_object(
            f"{placement.name}_Stem",
            data["stem"],
            parts_collection,
            assembly,
            (0.0, 0.0, STEM_ASSEMBLY_Z),
        )
        add_material_override(stem, materials[f"stem_{variant}"])
        stem["stem_variant"] = variant
        stem["connected_keycap"] = placement.keycap_name
        stem["mx_cross_post_actual_geometry"] = True
        stem["cross_to_collar_space"] = "open"
        stem["cross_post_uses_stem_material"] = True
        stem["exposed_geometry"] = "cylindrical_interface_only"
        tag_component(stem, part="stem", order=90, explode_vector=(0.0, 0.0, 14.0))

        spring = create_object(f"{placement.name}_Coil_Spring", data["spring"], parts_collection, assembly, (0.0, 0.0, 0.0))
        tag_component(spring, part="coil_spring", order=60, explode_vector=(0.0, 0.0, 5.0))

        click_bar = create_object(f"{placement.name}_Click_Bar", data["click_bar"], parts_collection, assembly, (0.0, 0.0, -0.15))
        tag_component(click_bar, part="click_bar", order=55, explode_vector=(-10.0, 0.0, 3.5))

        torsion = create_object(
            f"{placement.name}_Torsion_Spring",
            data["torsion_spring"],
            parts_collection,
            assembly,
            (-4.25, 0.0, -0.35),
        )
        tag_component(torsion, part="torsion_spring", order=50, explode_vector=(-9.0, 0.0, 1.0))

        fix_pin = create_object(f"{placement.name}_Fix_Pin", data["fix_pin"], parts_collection, assembly, (-5.15, 0.0, -0.35))
        tag_component(fix_pin, part="fix_pin", order=45, explode_vector=(-7.0, 0.0, -1.5))

        fixed = create_object(
            f"{placement.name}_Fixed_Contact",
            data["fixed_contact"],
            parts_collection,
            assembly,
            (5.90, 5.00, -1.15),
        )
        tag_component(fixed, part="fixed_contact", order=35, explode_vector=(9.0, 4.0, -2.0))

        moving = create_object(
            f"{placement.name}_Moving_Contact",
            data["moving_contact"],
            parts_collection,
            assembly,
            (5.90, 0.00, -0.95),
        )
        tag_component(moving, part="moving_contact", order=40, explode_vector=(9.0, -4.0, -1.0))

        push_rod = create_object(
            f"{placement.name}_Push_Rod",
            data["push_rod"],
            parts_collection,
            assembly,
            (3.25, -0.10, -0.15),
        )
        tag_component(push_rod, part="push_rod", order=65, explode_vector=(11.0, 0.0, 2.5))

        base = create_object(f"{placement.name}_Base", data["base"], parts_collection, assembly, (0.0, 0.0, -2.65))
        tag_component(base, part="base", order=10, explode_vector=(0.0, 0.0, -8.0))

        keycap = bpy.data.objects.get(placement.keycap_name)
        if keycap is not None:
            keycap["switch_assembly"] = assembly.name
            keycap["switch_model"] = "Kailh Choc V2 (PG1353)"
            keycap["stem_variant"] = variant

        part_count += 10

    bpy.context.view_layer.update()
    return {
        "switch_count": len(placements),
        "blue_stem_count": blue_count,
        "brown_stem_count": brown_count,
        "generated_component_count": part_count,
        "revision": REVISION,
        "dimensions_mm": {
            "outer_width": 15.0,
            "outer_depth": 15.0,
            "housing_height": 5.30,
            "stem_diameter": STEM_INTERFACE_DIAMETER_MM,
            "cover_stem_opening_diameter": COVER_STEM_OPENING_DIAMETER_MM,
            "cover_stem_radial_clearance": (
                COVER_STEM_OPENING_DIAMETER_MM - STEM_INTERFACE_DIAMETER_MM
            ) / 2.0,
            "mx_cross_post_length": MX_CROSS_POST_LENGTH_MM,
            "mx_cross_post_width": MX_CROSS_POST_WIDTH_MM,
            "stem_collar_inner_diameter": STEM_COLLAR_INNER_DIAMETER_MM,
            "stem_cross_post_top_inset": (
                STEM_INTERFACE_TOP_LOCAL_Z - MX_CROSS_POST_TOP_LOCAL_Z
            ),
            "cover_height": HOUSING_TOP_Z - COVER_BOTTOM_Z,
            "stem_collar_height": (
                STEM_INTERFACE_TOP_LOCAL_Z - STEM_INTERFACE_BOTTOM_LOCAL_Z
            ),
            "stem_collar_seat_offset": (
                STEM_ASSEMBLY_Z + STEM_INTERFACE_BOTTOM_LOCAL_Z - HOUSING_TOP_Z
            ),
            "stem_exposed_above_cover": (
                STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - HOUSING_TOP_Z
            ),
            "drawing_6_40_height": (
                STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - COVER_BOTTOM_Z
            ),
            "external_height_excluding_pins": (
                STEM_ASSEMBLY_Z + STEM_INTERFACE_TOP_LOCAL_Z - HOUSING_BOTTOM_Z
            ),
            "electrical_pin_protrusion": (
                HOUSING_BOTTOM_Z - ELECTRICAL_PIN_BOTTOM_Z
            ),
            "base_width": 13.95,
            "base_depth": 13.95,
        },
    }


if __name__ == "__main__":
    RESULT = build()
