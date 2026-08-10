"""Verify CPG135001S30 mesh dimensions and PCB-hole alignment."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".tmp/socket-model"


def load_socket_module():
    module_path = Path(__file__).with_name("build_choc_hotswap_sockets.py")
    spec = importlib.util.spec_from_file_location("akdk_socket_builder_verify", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def solve_3x3(matrix: list[list[float]], values: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Singular circle-fit matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(3):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][3] for row in range(3)]


def fit_circle(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    rows = [(2 * x, 2 * y, 1.0) for x, y in points]
    values = [x * x + y * y for x, y in points]
    matrix = [
        [sum(row[i] * row[j] for row in rows) for j in range(3)]
        for i in range(3)
    ]
    vector = [
        sum(row[i] * value for row, value in zip(rows, values)) for i in range(3)
    ]
    center_x, center_y, constant = solve_3x3(matrix, vector)
    radius = math.sqrt(max(0.0, center_x * center_x + center_y * center_y + constant))
    return center_x, center_y, radius


def local_boss_circles(module, base: bpy.types.Object) -> list[tuple[float, float, float]]:
    circles = []
    for expected_center in (module.LOCAL_CONTACT_A, module.LOCAL_CONTACT_B):
        points = []
        for vertex in base.data.vertices:
            if vertex.co.z <= 0.08:
                continue
            distance = math.hypot(
                vertex.co.x - expected_center[0], vertex.co.y - expected_center[1]
            )
            outer_radius = module.BOSS_OUTER_DIAMETER / 2
            if outer_radius - 0.20 < distance < outer_radius + 0.20:
                points.append((vertex.co.x, vertex.co.y))
        center_x, center_y, _fitted_radius = fit_circle(points)
        outer_radius = max(
            math.hypot(x - center_x, y - center_y) for x, y in points
        )
        circles.append((center_x, center_y, outer_radius))
    return circles


def transform_xy(root: bpy.types.Object, point: tuple[float, float]) -> tuple[float, float]:
    angle = root.rotation_euler.z
    cosine, sine = math.cos(angle), math.sin(angle)
    return (
        root.location.x + point[0] * cosine - point[1] * sine,
        root.location.y + point[0] * sine + point[1] * cosine,
    )


def mesh_edges_svg(
    obj: bpy.types.Object,
    *,
    projection: str,
    stroke: str,
    opacity: float,
) -> str:
    paths = []
    for edge in obj.data.edges:
        start = obj.data.vertices[edge.vertices[0]].co
        end = obj.data.vertices[edge.vertices[1]].co
        if projection == "top":
            x1, y1, x2, y2 = start.x, -start.y, end.x, -end.y
        else:
            x1, y1, x2, y2 = start.x, -start.z, end.x, -end.z
        paths.append(f"M{x1:.4f},{y1:.4f} L{x2:.4f},{y2:.4f}")
    return (
        f'<path d="{" ".join(paths)}" fill="none" stroke="{stroke}" '
        f'stroke-width="0.035" opacity="{opacity}" />'
    )


def top_overlay_svg(module, base: bpy.types.Object, contacts: bpy.types.Object) -> str:
    half_body_x = module.BODY_LENGTH / 2
    half_body_y = module.BODY_WIDTH / 2
    half_total_x = module.TERMINAL_OVERALL_LENGTH / 2
    circles = "\n".join(
        f'<circle cx="{center[0]}" cy="{-center[1]}" r="{module.BOSS_OUTER_DIAMETER / 2}" />'
        for center in (module.LOCAL_CONTACT_A, module.LOCAL_CONTACT_B)
    )
    reference = f"""
      <rect x="{-half_body_x}" y="{-half_body_y}" width="{module.BODY_LENGTH}" height="{module.BODY_WIDTH}" />
      <line x1="{-half_total_x}" y1="0" x2="{half_total_x}" y2="0" />
      {circles}
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="-7.6 -4.5 15.2 9.0">
  <rect x="-7.6" y="-4.5" width="15.2" height="9.0" fill="#111318" />
  <g fill="none" stroke="#28d17c" stroke-width="0.09" opacity="0.95">{reference}</g>
  {mesh_edges_svg(base, projection="top", stroke="#ff405d", opacity=0.62)}
  {mesh_edges_svg(contacts, projection="top", stroke="#ffb000", opacity=0.78)}
  <text x="-7.2" y="-3.8" fill="#fff" font-size="0.48">Top: green datasheet dimensions / red-orange generated mesh</text>
</svg>
"""


def side_overlay_svg(module, base: bpy.types.Object, contacts: bpy.types.Object) -> str:
    half_total_x = module.TERMINAL_OVERALL_LENGTH / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="-7.6 -2.0 15.2 4.9">
  <rect x="-7.6" y="-2.0" width="15.2" height="4.9" fill="#111318" />
  <g fill="none" stroke="#28d17c" stroke-width="0.09" opacity="0.95">
    <rect x="{-half_total_x}" y="{-module.BOSS_HEIGHT}" width="{module.TERMINAL_OVERALL_LENGTH}" height="{module.OVERALL_HEIGHT}" />
    <line x1="{-module.BODY_LENGTH / 2}" y1="0" x2="{module.BODY_LENGTH / 2}" y2="0" />
  </g>
  {mesh_edges_svg(base, projection="side", stroke="#ff405d", opacity=0.65)}
  {mesh_edges_svg(contacts, projection="side", stroke="#ffb000", opacity=0.8)}
  <text x="-7.2" y="-1.5" fill="#fff" font-size="0.48">Side: green 13.15 x 3.05 mm envelope / generated mesh</text>
</svg>
"""


def verify() -> dict:
    module = load_socket_module()
    base = bpy.data.objects.get("Left_Socket_01_Base")
    contacts = bpy.data.objects.get("Left_Socket_01_Contacts")
    if base is None or contacts is None:
        raise RuntimeError("Representative CPG135001S30 socket meshes are missing")

    base_bounds = [[min(c[i] for c in base.bound_box), max(c[i] for c in base.bound_box)] for i in range(3)]
    contact_bounds = [[min(c[i] for c in contacts.bound_box), max(c[i] for c in contacts.bound_box)] for i in range(3)]
    circles = local_boss_circles(module, base)
    actual_dimensions = {
        "body_length_mm": base_bounds[0][1] - base_bounds[0][0],
        "body_width_mm": base_bounds[1][1] - base_bounds[1][0],
        "body_height_mm": abs(base_bounds[2][0]),
        "overall_length_mm": contact_bounds[0][1] - contact_bounds[0][0],
        "overall_height_mm": base_bounds[2][1] - base_bounds[2][0],
        "boss_outer_diameter_mm": max(circle[2] * 2 for circle in circles),
        "contact_offset_x_mm": circles[1][0] - circles[0][0],
        "contact_offset_y_mm": abs(circles[1][1] - circles[0][1]),
    }
    reference_dimensions = {
        "body_length_mm": module.BODY_LENGTH,
        "body_width_mm": module.BODY_WIDTH,
        "body_height_mm": module.BODY_HEIGHT,
        "overall_length_mm": module.TERMINAL_OVERALL_LENGTH,
        "overall_height_mm": module.OVERALL_HEIGHT,
        "boss_outer_diameter_mm": module.BOSS_OUTER_DIAMETER,
        "contact_offset_x_mm": module.CONTACT_OFFSET_X,
        "contact_offset_y_mm": abs(module.CONTACT_OFFSET_Y),
    }
    dimension_errors = {
        key: abs(actual_dimensions[key] - reference_dimensions[key])
        for key in reference_dimensions
    }

    placement_errors = []
    side_counts = {}
    for side in ("Left", "Right"):
        data_path = module.PCB_DIR / f"Surround1x0-AKDK-{side.lower()}-pcb.json"
        data = json.loads(data_path.read_text())
        footprints = module.switch_socket_footprints(data)
        side_counts[side] = len(footprints)
        for index, footprint in enumerate(footprints, 1):
            root = bpy.data.objects.get(f"{side}_Socket_{index:02d}")
            if root is None:
                raise RuntimeError(f"Missing {side}_Socket_{index:02d}")
            for circle, reference_center in zip(
                circles, (footprint["contact_a"], footprint["contact_b"])
            ):
                actual_center = transform_xy(root, (circle[0], circle[1]))
                placement_errors.append(
                    math.hypot(
                        actual_center[0] - reference_center[0],
                        actual_center[1] - reference_center[1],
                    )
                )

    radial_clearance = (
        module.PCB_RECOMMENDED_HOLE_DIAMETER
        - actual_dimensions["boss_outer_diameter_mm"]
    ) / 2
    summary = {
        "part_number": "CPG135001S30",
        "datasheet": module.DATASHEET_RELATIVE_PATH,
        "socket_count": sum(side_counts.values()),
        "side_counts": side_counts,
        "reference_dimensions_mm": reference_dimensions,
        "actual_mesh_dimensions_mm": actual_dimensions,
        "dimension_errors_mm": dimension_errors,
        "max_dimension_error_mm": max(dimension_errors.values()),
        "max_boss_to_pcb_hole_center_error_mm": max(placement_errors),
        "boss_to_hole_radial_clearance_mm": radial_clearance,
        "alignment": {
            "transform": "EasyEDA x/y -> mm; per-footprint rigid XY rotation and translation",
            "anchors": "two 3.00 mm CPG135001S30 footprint hole centers",
        },
    }
    for folder in ("output", "overlay", "measurements"):
        (ARTIFACT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / "measurements/socket-summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    (ARTIFACT_ROOT / "output/socket-mesh-dimensions.json").write_text(
        json.dumps(actual_dimensions, indent=2)
    )
    (ARTIFACT_ROOT / "overlay/socket-top.svg").write_text(
        top_overlay_svg(module, base, contacts)
    )
    (ARTIFACT_ROOT / "overlay/socket-side.svg").write_text(
        side_overlay_svg(module, base, contacts)
    )

    if summary["socket_count"] != 45:
        raise RuntimeError(f"Expected 45 sockets, found {summary['socket_count']}")
    if summary["max_dimension_error_mm"] > 0.015:
        raise RuntimeError(f"Socket dimension mismatch: {summary}")
    if summary["max_boss_to_pcb_hole_center_error_mm"] > 0.01:
        raise RuntimeError(f"Socket-to-hole alignment mismatch: {summary}")
    return summary


if __name__ == "__main__":
    print("SOCKET_VERIFY=" + json.dumps(verify(), sort_keys=True))
