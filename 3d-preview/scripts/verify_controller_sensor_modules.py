"""Verify controller, conthrough and mouse-sensor dimensions/placement."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".tmp/controller-sensor-model"


def load_builder():
    module_path = Path(__file__).with_name("build_controller_sensor_modules.py")
    spec = importlib.util.spec_from_file_location("controller_sensor_verify_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data_dimensions(obj: bpy.types.Object) -> tuple[float, float, float]:
    coordinates = [vertex.co for vertex in obj.data.vertices]
    return tuple(
        max(point[index] for point in coordinates) - min(point[index] for point in coordinates)
        for index in range(3)
    )


def local_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    """Bounds in keyboard-half local coordinates, excluding exploded offsets."""
    points = [obj.matrix_basis @ vertex.co for vertex in obj.data.vertices]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def center_from_bounds(bounds: tuple[Vector, Vector]) -> Vector:
    return (bounds[0] + bounds[1]) / 2


def relative_matrix(obj: bpy.types.Object, ancestor: bpy.types.Object) -> Matrix:
    return ancestor.matrix_world.inverted() @ obj.matrix_world


def relative_bounds(obj: bpy.types.Object, ancestor: bpy.types.Object) -> tuple[Vector, Vector]:
    matrix = relative_matrix(obj, ancestor)
    points = [matrix @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def measure_case_anchors(builder, side: str) -> dict:
    case = bpy.data.objects.get(f"{side}_Bottom_Case")
    if case is None:
        raise RuntimeError(f"Missing {side} lower case")
    points = [case.matrix_basis @ vertex.co for vertex in case.data.vertices]

    usb_x = builder.CASE_USB_APERTURE_X[side]
    usb_z = builder.CASE_USB_APERTURE_Z
    usb_y = builder.CASE_USB_WALL_Y[side]
    usb_points = [
        point for point in points
        if usb_x[0] - 0.05 <= point.x <= usb_x[1] + 0.05
        and abs(point.y - usb_y) <= 0.03
        and usb_z[0] - 0.05 <= point.z <= usb_z[1] + 0.05
    ]
    if len(usb_points) < 8:
        raise RuntimeError(f"Could not extract {side} USB aperture from lower-case mesh")
    usb_bounds = (
        Vector(tuple(min(point[index] for point in usb_points) for index in range(3))),
        Vector(tuple(max(point[index] for point in usb_points) for index in range(3))),
    )

    slot_x = builder.CASE_POWER_SLOT_X[side]
    slot_y = builder.CASE_POWER_SLOT_Y
    slot_z = builder.CASE_POWER_SLOT_Z
    slot_points = [
        point for point in points
        if slot_x[0] - 0.02 <= point.x <= slot_x[1] + 0.02
        and slot_y[0] - 0.02 <= point.y <= slot_y[1] + 0.02
        and slot_z[0] - 0.02 <= point.z <= slot_z[1] + 0.02
    ]
    if len(slot_points) < 4:
        raise RuntimeError(f"Could not extract {side} power-switch slot from lower-case mesh")
    slot_bounds = (
        Vector(tuple(min(point[index] for point in slot_points) for index in range(3))),
        Vector(tuple(max(point[index] for point in slot_points) for index in range(3))),
    )
    return {
        "usb_vertex_count": len(usb_points),
        "usb_min_mm": list(usb_bounds[0]),
        "usb_max_mm": list(usb_bounds[1]),
        "usb_center_mm": list(center_from_bounds(usb_bounds)),
        "power_slot_vertex_count": len(slot_points),
        "power_slot_min_mm": list(slot_bounds[0]),
        "power_slot_max_mm": list(slot_bounds[1]),
        "power_slot_center_mm": list(center_from_bounds(slot_bounds)),
    }


def controller_svg(builder, side: str, board: bpy.types.Object, pads: list[dict]) -> str:
    reference = builder.board_outline(side)
    generated = []
    top_z = builder.CONTROLLER_TOP_Z
    for edge in board.data.edges:
        start = board.data.vertices[edge.vertices[0]].co
        end = board.data.vertices[edge.vertices[1]].co
        if abs(start.z - top_z) < 0.03 and abs(end.z - top_z) < 0.03:
            generated.append(f"M{start.x:.4f},{-start.y:.4f} L{end.x:.4f},{-end.y:.4f}")
    reference_path = " ".join(
        f"{'M' if index == 0 else 'L'}{x:.4f},{-y:.4f}"
        for index, (x, y) in enumerate(reference + [reference[0]])
    )
    circles = "\n".join(
        f'<circle cx="{pad["center"][0]:.4f}" cy="{-pad["center"][1]:.4f}" r="{builder.CONTHROUGH_HOLE_DIAMETER / 2:.4f}" />'
        for pad in pads
    )
    xmin = builder.BOARD_X_MIN[side] - 3
    ymax = builder.CONTROLLER_Y_MAX + 3
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin:.3f} {-ymax:.3f} {builder.CONTROLLER_LENGTH + 6:.3f} {builder.CONTROLLER_WIDTH + 6:.3f}">
  <rect x="{xmin:.3f}" y="{-ymax:.3f}" width="{builder.CONTROLLER_LENGTH + 6:.3f}" height="{builder.CONTROLLER_WIDTH + 6:.3f}" fill="#111318" />
  <path d="{reference_path}" fill="none" stroke="#26d17c" stroke-width="0.28" />
  <g fill="none" stroke="#26d17c" stroke-width="0.20">{circles}</g>
  <path d="{' '.join(generated)}" fill="none" stroke="#ff405d" stroke-width="0.13" opacity="0.86" />
  <text x="{xmin + 1.4:.3f}" y="{-ymax + 2.2:.3f}" fill="#fff" font-size="1.45">{side} Auto-KDK — green: official/EasyEDA reference, red: generated mesh</text>
</svg>
"""


def sensor_svg(builder, board: bpy.types.Object) -> str:
    paths = []
    for edge in board.data.edges:
        start = board.data.vertices[edge.vertices[0]].co
        end = board.data.vertices[edge.vertices[1]].co
        if start.z > 0.45 and end.z > 0.45:
            paths.append(f"M{start.x:.4f},{-start.y:.4f} L{end.x:.4f},{-end.y:.4f}")
    slot_centers = [(-2.55, -5.25), (2.55, -5.25), (-2.55, 5.25), (2.55, 5.25)]
    slots = "\n".join(
        f'<rect x="{cx - builder.SENSOR_SLOT_LENGTH / 2:.4f}" y="{-cy - builder.SENSOR_SLOT_WIDTH / 2:.4f}" width="{builder.SENSOR_SLOT_LENGTH:.4f}" height="{builder.SENSOR_SLOT_WIDTH:.4f}" rx="{builder.SENSOR_SLOT_WIDTH / 2:.4f}" />'
        for cx, cy in slot_centers
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="-5.7 -8.7 11.4 17.4">
  <rect x="-5.7" y="-8.7" width="11.4" height="17.4" fill="#111318" />
  <g fill="none" stroke="#26d17c" stroke-width="0.13">
    <rect x="{-builder.SENSOR_WIDTH / 2}" y="{-builder.SENSOR_LENGTH / 2}" width="{builder.SENSOR_WIDTH}" height="{builder.SENSOR_LENGTH}" />
    {slots}
  </g>
  <path d="{' '.join(paths)}" fill="none" stroke="#ff405d" stroke-width="0.075" opacity="0.90" />
  <text x="-5.3" y="-7.9" fill="#fff" font-size="0.55">Mouse sensor 13.4 x 7.4 mm — reference/generated overlay</text>
</svg>
"""


def verify() -> dict:
    builder = load_builder()
    keyboard_root = bpy.data.objects.get("Keyboard_Root")
    if keyboard_root is not None:
        keyboard_root["exploded_view_enabled"] = False
    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or obj.get("exploded_view_order") is None:
            continue
        if obj.animation_data is not None:
            for driver in obj.animation_data.drivers:
                if driver.data_path == "location" and driver.array_index == 2:
                    driver.mute = True
        obj.location.z = 0
    bpy.context.view_layer.update()

    controller_summaries = {}
    pitch_errors = []
    separation_errors = []
    for side in ("Left", "Right"):
        board = bpy.data.objects.get(f"{side}_Controller_PCB")
        assembly = bpy.data.objects.get(f"{side}_Controller_Assembly")
        conthrough = bpy.data.objects.get(f"{side}_Conthrough_Assembly")
        if board is None or assembly is None or conthrough is None:
            raise RuntimeError(f"Missing {side} controller/conthrough assembly")
        footprint = builder.controller_footprint(side)
        board_holes = builder.controller_board_holes(side, footprint)
        dimensions = data_dimensions(board)
        wires = [
            obj for obj in bpy.data.objects
            if obj.get("component_family") == "conthrough"
            and obj.get("component_role") == "spring_pin"
            and obj.get("component_side") == side
        ]
        pitch_error = abs(footprint["pitch"] - builder.CONTHROUGH_PITCH)
        separation_error = abs(footprint["row_separation"] - builder.CONTHROUGH_ROW_SEPARATION)
        pitch_errors.append(pitch_error)
        separation_errors.append(separation_error)
        footprint_centers = sorted(tuple(pad["center"]) for pad in footprint["pads"])
        wire_centers = sorted(
            tuple(float(value) for value in obj.get("conthrough_pad_center_mm", ()))
            for obj in wires
        )
        if any(len(center) != 2 for center in wire_centers):
            raise RuntimeError(f"Missing {side} conthrough pad-centre metadata")
        conthrough_registration_error = max(
            math.dist(reference, generated)
            for reference, generated in zip(footprint_centers, wire_centers)
        )
        all_board_hole_centers = [tuple(hole["center"]) for hole in board_holes]
        selected_hole_registration_error = max(
            min(math.dist(reference, candidate) for candidate in all_board_hole_centers)
            for reference in footprint_centers
        )
        case_anchors = measure_case_anchors(builder, side)
        usb = bpy.data.objects.get(f"{side}_Controller_USB_C")
        usb_mouth = bpy.data.objects.get(f"{side}_Controller_USB_C_Mouth")
        usb_cavity = bpy.data.objects.get(f"{side}_Controller_USB_C_Cavity")
        usb_tongue = bpy.data.objects.get(f"{side}_Controller_USB_C_Tongue")
        usb_contacts = bpy.data.objects.get(f"{side}_Controller_USB_C_Contacts")
        actuator = bpy.data.objects.get(f"{side}_Controller_Power_Switch_Actuator")
        battery = bpy.data.objects.get(f"{side}_Controller_LiPo_400mAh")
        housings = [
            bpy.data.objects.get(f"{side}_Conthrough_Row_{index}_Housing")
            for index in (1, 2)
        ]
        if (
            usb is None
            or usb_mouth is None
            or usb_cavity is None
            or usb_tongue is None
            or usb_contacts is None
            or actuator is None
            or battery is None
            or any(item is None for item in housings)
        ):
            raise RuntimeError(f"Missing {side} case-alignment component")
        usb_bounds = local_bounds(usb)
        usb_mouth_bounds = local_bounds(usb_mouth)
        usb_cavity_bounds = local_bounds(usb_cavity)
        usb_tongue_bounds = local_bounds(usb_tongue)
        board_bounds = local_bounds(board)
        actuator_bounds = local_bounds(actuator)
        battery_bounds = local_bounds(battery)
        housing_bounds = [local_bounds(item) for item in housings]
        usb_center = center_from_bounds(usb_bounds)
        actuator_center = center_from_bounds(actuator_bounds)
        case_usb_center = Vector(case_anchors["usb_center_mm"])
        case_slot_center = Vector(case_anchors["power_slot_center_mm"])
        usb_clearances_xz = [
            usb_bounds[0].x - case_anchors["usb_min_mm"][0],
            case_anchors["usb_max_mm"][0] - usb_bounds[1].x,
            usb_bounds[0].z - case_anchors["usb_min_mm"][2],
            case_anchors["usb_max_mm"][2] - usb_bounds[1].z,
        ]
        controller_summaries[side] = {
            "mesh_dimensions_mm": list(dimensions),
            "through_hole_count": int(board.get("actual_through_holes", 0)),
            "selected_conthrough_hole_count": int(board.get("selected_conthrough_holes", 0)),
            "available_pitch_variants_mm": list(board.get("available_pitch_variants_mm", [])),
            "conthrough_spring_pin_count": len(wires),
            "selected_hole_to_easyeda_error_mm": selected_hole_registration_error,
            "conthrough_pin_to_easyeda_error_mm": conthrough_registration_error,
            "placement_anchor": assembly.get("controller_placement_anchor"),
            "footprint_pitch_mm": footprint["pitch"],
            "footprint_row_separation_mm": footprint["row_separation"],
            "mounting_side": assembly.get("controller_mounting_side"),
            "pcb_to_controller_gap_mm": builder.MAIN_PCB_BOTTOM_Z - builder.CONTROLLER_TOP_Z,
            "main_pcb_bottom_z_mm": builder.MAIN_PCB_BOTTOM_Z,
            "controller_top_z_mm": builder.CONTROLLER_TOP_Z,
            "controller_bottom_z_mm": builder.CONTROLLER_BOTTOM_Z,
            "case_anchors": case_anchors,
            "usb_center_mm": list(usb_center),
            "usb_aperture_horizontal_center_error_mm": abs(usb_center.x - case_usb_center.x),
            "usb_bounds_mm": {"min": list(usb_bounds[0]), "max": list(usb_bounds[1])},
            "usb_aperture_clearances_xz_mm": usb_clearances_xz,
            "usb_minimum_aperture_clearance_xz_mm": min(usb_clearances_xz),
            "usb_inside_case_aperture_xz": bool(
                usb_bounds[0].x >= case_anchors["usb_min_mm"][0] - 0.01
                and usb_bounds[1].x <= case_anchors["usb_max_mm"][0] + 0.01
                and usb_bounds[0].z >= case_anchors["usb_min_mm"][2] - 0.01
                and usb_bounds[1].z <= case_anchors["usb_max_mm"][2] + 0.01
            ),
            "usb_receptacle": {
                "case_outer_wall_y_mm": case_anchors["usb_center_mm"][1],
                "mouth_outer_face_y_mm": usb_mouth_bounds[1].y,
                "mouth_case_recess_mm": case_anchors["usb_center_mm"][1] - usb_mouth_bounds[1].y,
                "shell_dimensions_mm": [
                    usb_bounds[1].x - usb_bounds[0].x,
                    usb_bounds[1].y - usb_bounds[0].y,
                    usb_bounds[1].z - usb_bounds[0].z,
                ],
                "mouth_dimensions_mm": [
                    usb_mouth_bounds[1].x - usb_mouth_bounds[0].x,
                    usb_mouth_bounds[1].y - usb_mouth_bounds[0].y,
                    usb_mouth_bounds[1].z - usb_mouth_bounds[0].z,
                ],
                "mouth_opening_mm": [
                    float(usb_mouth.get("opening_width_mm", 0)),
                    float(usb_mouth.get("opening_height_mm", 0)),
                ],
                "cavity_dimensions_mm": [
                    usb_cavity_bounds[1].x - usb_cavity_bounds[0].x,
                    usb_cavity_bounds[1].y - usb_cavity_bounds[0].y,
                    usb_cavity_bounds[1].z - usb_cavity_bounds[0].z,
                ],
                "tongue_dimensions_mm": [
                    usb_tongue_bounds[1].x - usb_tongue_bounds[0].x,
                    usb_tongue_bounds[1].y - usb_tongue_bounds[0].y,
                    usb_tongue_bounds[1].z - usb_tongue_bounds[0].z,
                ],
                "contact_count": int(usb_contacts.get("contact_count", 0)),
                "contact_pitch_mm": float(usb_contacts.get("contact_pitch_mm", 0)),
            },
            "pcb_case_wall_recess_mm": case_anchors["usb_center_mm"][1] - board_bounds[1].y,
            "pcb_y_bounds_mm": [board_bounds[0].y, board_bounds[1].y],
            "power_actuator_center_mm": list(actuator_center),
            "power_slot_xy_error_mm": [
                abs(actuator_center.x - case_slot_center.x),
                abs(actuator_center.y - case_slot_center.y),
            ],
            "power_actuator_bounds_mm": {
                "min": list(actuator_bounds[0]),
                "max": list(actuator_bounds[1]),
            },
            "power_actuator_inside_slot_xy": bool(
                actuator_bounds[0].x >= case_anchors["power_slot_min_mm"][0] - 0.01
                and actuator_bounds[1].x <= case_anchors["power_slot_max_mm"][0] + 0.01
                and actuator_bounds[0].y >= case_anchors["power_slot_min_mm"][1] - 0.01
                and actuator_bounds[1].y <= case_anchors["power_slot_max_mm"][1] + 0.01
            ),
            "battery_case_support_residual_mm": battery_bounds[0].z - builder.CASE_CONTROLLER_SUPPORT_Z,
            "conthrough_housing_z_bounds_mm": [
                [bounds[0].z, bounds[1].z] for bounds in housing_bounds
            ],
            "controller_layer": assembly.get("exploded_view_layer"),
            "conthrough_layer": conthrough.get("exploded_view_layer"),
        }
        (ARTIFACT_ROOT / "overlay").mkdir(parents=True, exist_ok=True)
        (ARTIFACT_ROOT / f"overlay/{side.lower()}-controller-top.svg").write_text(
            controller_svg(builder, side, board, board_holes)
        )

    sensor = bpy.data.objects.get("Right_Mouse_Sensor_PCB")
    sensor_assembly = bpy.data.objects.get("Right_Mouse_Sensor_Assembly")
    fpc = bpy.data.objects.get("Right_Mouse_Sensor_FPC_Ribbon")
    if sensor is None or sensor_assembly is None or fpc is None:
        raise RuntimeError("Mouse sensor PCB/FPC assembly is missing")
    sensor_dimensions = data_dimensions(sensor)
    sensor_summary = {
        "mesh_dimensions_mm": list(sensor_dimensions),
        "mounting_slot_count": int(sensor.get("actual_mounting_slots", 0)),
        "fpc_pin_count": int(fpc.get("fpc_pin_count", 0)),
        "fpc_pitch_mm": float(fpc.get("fpc_pitch_mm", 0)),
        "fpc_width_mm": float(fpc.get("fpc_width_mm", 0)),
        "exploded_layer": sensor_assembly.get("exploded_view_layer"),
    }
    right_half = bpy.data.objects["Right_Half_Root"]
    upper_lens = bpy.data.objects["Right_Mouse_Sensor_Upper_Lens"]
    sensor_connector = bpy.data.objects["Right_Mouse_Sensor_FPC_6P_Connector"]
    lens_matrix = relative_matrix(upper_lens, right_half)
    board_matrix = relative_matrix(sensor, right_half)
    lens_center = lens_matrix.translation
    connector_center = center_from_bounds(relative_bounds(sensor_connector, right_half))
    optical_axis = (board_matrix.to_3x3() @ Vector((0, 0, 1))).normalized()
    expected_axis = (builder.TRACKBALL_CENTER - builder.SENSOR_LENS_TARGET).normalized()
    sensor_summary.update(
        {
            "lens_center_mm": list(lens_center),
            "lens_target_error_mm": (lens_center - builder.SENSOR_LENS_TARGET).length,
            "optical_axis_angle_error_deg": math.degrees(optical_axis.angle(expected_axis)),
            "lens_to_ball_surface_clearance_mm": (
                (lens_center - builder.TRACKBALL_CENTER).length - builder.TRACKBALL_RADIUS
            ),
            "fpc_connector_center_mm": list(connector_center),
            "fpc_connector_toward_autokdk": connector_center.y > lens_center.y,
            "fpc_escape_groove_y_mm": float(fpc.get("case_escape_groove_mm")[1]),
            "mount": sensor_assembly.get("mouse_sensor_mount"),
        }
    )
    ribbon_vertices = [fpc.matrix_world @ vertex.co for vertex in fpc.data.vertices]
    ribbon_ends = [
        (ribbon_vertices[0] + ribbon_vertices[1]) / 2,
        (ribbon_vertices[-2] + ribbon_vertices[-1]) / 2,
    ]
    connector_centers = []
    for name in ("Right_Controller_FPC_6P_Connector", "Right_Mouse_Sensor_FPC_6P_Connector"):
        connector = bpy.data.objects.get(name)
        if connector is None:
            raise RuntimeError(f"Missing FPC connector: {name}")
        corners = [connector.matrix_world @ Vector(corner) for corner in connector.bound_box]
        connector_centers.append(
            Vector(
                tuple(
                    (min(point[index] for point in corners) + max(point[index] for point in corners)) / 2
                    for index in range(3)
                )
            )
        )
    sensor_summary["fpc_endpoint_errors_mm"] = [
        (ribbon_end - connector_center).length
        for ribbon_end, connector_center in zip(ribbon_ends, connector_centers)
    ]
    (ARTIFACT_ROOT / "overlay/sensor-module-top.svg").write_text(sensor_svg(builder, sensor))

    dimension_errors = {
        "controller_length": max(
            abs(summary["mesh_dimensions_mm"][0] - builder.CONTROLLER_LENGTH)
            for summary in controller_summaries.values()
        ),
        "controller_width": max(
            abs(summary["mesh_dimensions_mm"][1] - builder.CONTROLLER_WIDTH)
            for summary in controller_summaries.values()
        ),
        "controller_thickness": max(
            abs(summary["mesh_dimensions_mm"][2] - builder.CONTROLLER_THICKNESS)
            for summary in controller_summaries.values()
        ),
        "sensor_width": abs(sensor_dimensions[0] - builder.SENSOR_WIDTH),
        "sensor_length": abs(sensor_dimensions[1] - builder.SENSOR_LENGTH),
        "sensor_thickness": abs(sensor_dimensions[2] - builder.SENSOR_THICKNESS),
    }
    summary = {
        "revision": builder.REVISION,
        "references": {
            "controller": builder.AUTO_KDK_SOURCE,
            "sensor": builder.SENSOR_SOURCE,
        },
        "controllers": controller_summaries,
        "sensor": sensor_summary,
        "max_dimension_error_mm": max(dimension_errors.values()),
        "max_pin_pitch_error_mm": max(pitch_errors),
        "max_row_separation_error_mm": max(separation_errors),
        "dimension_errors_mm": dimension_errors,
        "case_alignment": {
            "placement_anchor": "repository EasyEDA conthrough rows; case openings are clearance checks only",
            "maximum_selected_hole_to_easyeda_error_mm": max(
                item["selected_hole_to_easyeda_error_mm"] for item in controller_summaries.values()
            ),
            "maximum_conthrough_pin_to_easyeda_error_mm": max(
                item["conthrough_pin_to_easyeda_error_mm"] for item in controller_summaries.values()
            ),
            "minimum_usb_aperture_clearance_xz_mm": min(
                item["usb_minimum_aperture_clearance_xz_mm"]
                for item in controller_summaries.values()
            ),
            "minimum_pcb_case_wall_recess_mm": min(
                item["pcb_case_wall_recess_mm"]
                for item in controller_summaries.values()
            ),
            "maximum_power_slot_xy_error_mm": max(
                max(item["power_slot_xy_error_mm"]) for item in controller_summaries.values()
            ),
            "maximum_battery_support_residual_mm": max(
                abs(item["battery_case_support_residual_mm"])
                for item in controller_summaries.values()
            ),
        },
    }
    (ARTIFACT_ROOT / "measurements").mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / "measurements/controller-sensor-summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    if summary["max_dimension_error_mm"] > 0.015:
        raise RuntimeError(f"Controller/sensor dimension mismatch: {summary}")
    if summary["max_pin_pitch_error_mm"] > 0.002:
        raise RuntimeError(f"Conthrough pitch mismatch: {summary}")
    if summary["max_row_separation_error_mm"] > 0.002:
        raise RuntimeError(f"Conthrough row separation mismatch: {summary}")
    if any(item["through_hole_count"] != 45 for item in controller_summaries.values()):
        raise RuntimeError(f"Controller through-hole count mismatch: {summary}")
    if any(item["selected_conthrough_hole_count"] != 18 for item in controller_summaries.values()):
        raise RuntimeError(f"Controller selected-hole count mismatch: {summary}")
    if any(item["available_pitch_variants_mm"] != [19, 18, 17, 16] for item in controller_summaries.values()):
        raise RuntimeError(f"Controller pitch-variant hole grid mismatch: {summary}")
    if any(item["conthrough_spring_pin_count"] != 18 for item in controller_summaries.values()):
        raise RuntimeError(f"Conthrough pin count mismatch: {summary}")
    if any(item["mounting_side"] != "below main PCB, component side down" for item in controller_summaries.values()):
        raise RuntimeError(f"Controller mounting-side mismatch: {summary}")
    if any(not math.isclose(item["pcb_to_controller_gap_mm"], 2.5, abs_tol=0.002) for item in controller_summaries.values()):
        raise RuntimeError(f"Controller vertical gap mismatch: {summary}")
    if any(not item["usb_inside_case_aperture_xz"] for item in controller_summaries.values()):
        raise RuntimeError(f"USB-C does not fit lower-case aperture: {summary}")
    if any(
        item["usb_aperture_horizontal_center_error_mm"] > 0.002
        for item in controller_summaries.values()
    ):
        raise RuntimeError(f"USB-C is not horizontally centred in lower-case aperture: {summary}")
    for item in controller_summaries.values():
        receptacle = item["usb_receptacle"]
        if not math.isclose(
            receptacle["mouth_opening_mm"][0],
            builder.USB_C_SHELL_OPENING_WIDTH,
            abs_tol=0.002,
        ) or not math.isclose(
            receptacle["mouth_opening_mm"][1],
            builder.USB_C_SHELL_OPENING_HEIGHT,
            abs_tol=0.002,
        ):
            raise RuntimeError(f"USB-C shell opening mismatch: {summary}")
        if not math.isclose(
            receptacle["shell_dimensions_mm"][1],
            builder.USB_C_SHELL_DEPTH,
            abs_tol=0.002,
        ):
            raise RuntimeError(f"USB-C shell length mismatch: {summary}")
        if not math.isclose(
            receptacle["tongue_dimensions_mm"][0],
            builder.USB_C_TONGUE_WIDTH,
            abs_tol=0.002,
        ) or not math.isclose(
            receptacle["tongue_dimensions_mm"][2],
            builder.USB_C_TONGUE_HEIGHT,
            abs_tol=0.002,
        ):
            raise RuntimeError(f"USB-C tongue mismatch: {summary}")
        if receptacle["contact_count"] != builder.USB_C_CONTACT_COUNT_PER_SIDE * 2:
            raise RuntimeError(f"USB-C contact count mismatch: {summary}")
        if not math.isclose(
            receptacle["contact_pitch_mm"],
            builder.USB_C_CONTACT_PITCH,
            abs_tol=0.002,
        ):
            raise RuntimeError(f"USB-C contact pitch mismatch: {summary}")
        expected_recess = (
            receptacle["case_outer_wall_y_mm"]
            - (builder.USB_C_SHELL_FRONT_Y + builder.USB_C_MOUTH_DEPTH)
        )
        if receptacle["mouth_case_recess_mm"] < builder.USB_C_FACE_RECESS - 0.002:
            raise RuntimeError(f"USB-C mouth protrudes through lower-case wall: {summary}")
        if not math.isclose(
            receptacle["mouth_case_recess_mm"],
            expected_recess,
            abs_tol=0.002,
        ):
            raise RuntimeError(f"USB-C mouth wall-recess target mismatch: {summary}")
    if summary["case_alignment"]["minimum_pcb_case_wall_recess_mm"] < 0.75:
        raise RuntimeError(f"Controller PCB protrudes through lower-case wall: {summary}")
    if not math.isclose(
        summary["case_alignment"]["minimum_pcb_case_wall_recess_mm"],
        builder.CONTROLLER_CASE_WALL_RECESS,
        abs_tol=0.02,
    ):
        raise RuntimeError(f"Controller PCB wall recess target mismatch: {summary}")
    if any(not item["power_actuator_inside_slot_xy"] for item in controller_summaries.values()):
        raise RuntimeError(f"Power actuator does not fit lower-case slot: {summary}")
    if summary["case_alignment"]["maximum_selected_hole_to_easyeda_error_mm"] > 0.002:
        raise RuntimeError(f"Controller selected holes do not match EasyEDA: {summary}")
    if summary["case_alignment"]["maximum_conthrough_pin_to_easyeda_error_mm"] > 0.002:
        raise RuntimeError(f"Conthrough pins do not match EasyEDA: {summary}")
    if summary["case_alignment"]["maximum_power_slot_xy_error_mm"] > 0.02:
        raise RuntimeError(f"Power-slot centre mismatch: {summary}")
    if summary["case_alignment"]["maximum_battery_support_residual_mm"] > 0.10:
        raise RuntimeError(f"Battery/lower-case support mismatch: {summary}")
    for item in controller_summaries.values():
        for z_min, z_max in item["conthrough_housing_z_bounds_mm"]:
            if not math.isclose(z_min, builder.CONTROLLER_TOP_Z, abs_tol=0.002) or not math.isclose(
                z_max, builder.MAIN_PCB_BOTTOM_Z, abs_tol=0.002
            ):
                raise RuntimeError(f"Conthrough vertical span mismatch: {summary}")
    if sensor_summary["mounting_slot_count"] != 4:
        raise RuntimeError(f"Sensor mounting-slot count mismatch: {summary}")
    if sensor_summary["fpc_pin_count"] != 6 or not math.isclose(sensor_summary["fpc_pitch_mm"], 0.5):
        raise RuntimeError(f"Sensor FPC mismatch: {summary}")
    if max(sensor_summary["fpc_endpoint_errors_mm"]) > 0.25:
        raise RuntimeError(f"Sensor FPC connector alignment mismatch: {summary}")
    if sensor_summary["lens_target_error_mm"] > 0.002:
        raise RuntimeError(f"Sensor lens does not match the top-case aperture: {summary}")
    if sensor_summary["optical_axis_angle_error_deg"] > 1.0:
        raise RuntimeError(f"Sensor optical axis does not point at the trackball: {summary}")
    if not 0.0 <= sensor_summary["lens_to_ball_surface_clearance_mm"] <= 0.5:
        raise RuntimeError(f"Sensor lens/trackball clearance mismatch: {summary}")
    if not sensor_summary["fpc_connector_toward_autokdk"]:
        raise RuntimeError(f"Sensor FPC connector faces away from Auto-KDK: {summary}")
    if not math.isclose(sensor_summary["fpc_escape_groove_y_mm"], builder.SENSOR_FPC_GROOVE_Y, abs_tol=0.002):
        raise RuntimeError(f"Sensor FPC does not use the adjacent case groove: {summary}")
    if any(item["controller_layer"] != "controller" for item in controller_summaries.values()):
        raise RuntimeError(f"Controller Exploded View layer mismatch: {summary}")
    if any(item["conthrough_layer"] != "conthrough" for item in controller_summaries.values()):
        raise RuntimeError(f"Conthrough Exploded View layer mismatch: {summary}")
    if sensor_summary["exploded_layer"] != "mouse_sensor":
        raise RuntimeError(f"Sensor Exploded View layer mismatch: {summary}")
    return summary


if __name__ == "__main__":
    print("CONTROLLER_SENSOR_VERIFY=" + json.dumps(verify(), sort_keys=True))
