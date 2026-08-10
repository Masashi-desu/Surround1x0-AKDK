"""Verify generated PCB drill rims against the EasyEDA source coordinates."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".tmp/pcb-hole-verification"


def solve_3x3(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Solve a small linear system with partial pivoting."""
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


def fit_circle(vertices) -> tuple[float, float, float]:
    """Fit a circle to Boolean-generated rim vertices without centroid bias."""
    rows = [(2.0 * vertex.x, 2.0 * vertex.y, 1.0) for vertex in vertices]
    values = [vertex.x * vertex.x + vertex.y * vertex.y for vertex in vertices]
    normal_matrix = [
        [sum(row[i] * row[j] for row in rows) for j in range(3)]
        for i in range(3)
    ]
    normal_values = [
        sum(row[i] * value for row, value in zip(rows, values)) for i in range(3)
    ]
    center_x, center_y, constant = solve_3x3(normal_matrix, normal_values)
    radius = math.sqrt(max(0.0, center_x * center_x + center_y * center_y + constant))
    return center_x, center_y, radius


def load_builder_module():
    module_path = Path(__file__).with_name("build_pcb_from_repository.py")
    spec = importlib.util.spec_from_file_location("akdk_pcb_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def svg_document(
    side: str,
    outline: list[tuple[float, float]],
    expected: list[tuple[tuple[float, float], float]],
    measured: list[dict],
    *,
    crop: tuple[float, float, float, float] | None = None,
) -> str:
    if crop is None:
        xs = [point[0] for point in outline]
        ys = [point[1] for point in outline]
        minimum_x, maximum_x = min(xs) - 4, max(xs) + 4
        minimum_y, maximum_y = min(ys) - 4, max(ys) + 4
    else:
        minimum_x, minimum_y, maximum_x, maximum_y = crop
    width = maximum_x - minimum_x
    height = maximum_y - minimum_y
    view_y = -maximum_y
    outline_points = " ".join(f"{x:.4f},{-y:.4f}" for x, y in outline)
    expected_circles = "\n".join(
        f'<circle cx="{center[0]:.4f}" cy="{-center[1]:.4f}" r="{diameter / 2:.4f}" />'
        for center, diameter in expected
    )
    measured_circles = "\n".join(
        f'<circle cx="{item["actual_center_mm"][0]:.4f}" cy="{-item["actual_center_mm"][1]:.4f}" r="{item["actual_diameter_mm"] / 2:.4f}" />'
        for item in measured
        if item["matched"]
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minimum_x:.4f} {view_y:.4f} {width:.4f} {height:.4f}">
  <rect x="{minimum_x:.4f}" y="{view_y:.4f}" width="{width:.4f}" height="{height:.4f}" fill="#111318" />
  <polyline points="{outline_points}" fill="none" stroke="#aeb5c0" stroke-width="0.28" />
  <g fill="none" stroke="#28d17c" stroke-width="0.24" opacity="0.92">
    {expected_circles}
  </g>
  <g fill="none" stroke="#ff405d" stroke-width="0.14" opacity="0.9">
    {measured_circles}
  </g>
  <text x="{minimum_x + 2:.4f}" y="{view_y + 3:.4f}" fill="#ffffff" font-size="2.2">{side} PCB — green: EasyEDA reference / red: generated mesh</text>
</svg>
"""


def verify_side(builder, side: str) -> dict:
    data_path = builder.PCB_DIR / f"Surround1x0-AKDK-{side.lower()}-pcb.json"
    data = json.loads(data_path.read_text())
    expected = builder.collect_drill_holes(data)
    outline = builder.board_outline(data)
    board = bpy.data.objects.get(f"{side}_PCB_Substrate")
    if board is None or board.type != "MESH":
        raise RuntimeError(f"Missing generated mesh: {side}_PCB_Substrate")

    top_vertices = [
        vertex.co.copy()
        for vertex in board.data.vertices
        if abs(vertex.co.z - builder.BOARD_TOP_Z) < 0.03
    ]
    measured = []
    for index, (center, diameter) in enumerate(expected):
        radius = diameter / 2
        rim = []
        for vertex in top_vertices:
            distance = math.hypot(vertex.x - center[0], vertex.y - center[1])
            if abs(distance - radius) < 0.055:
                rim.append(vertex)
        matched = len(rim) >= 8
        if matched:
            actual_x, actual_y, actual_radius = fit_circle(rim)
            center_error = math.hypot(actual_x - center[0], actual_y - center[1])
            diameter_error = abs(actual_radius * 2 - diameter)
        else:
            actual_x = actual_y = actual_radius = center_error = diameter_error = None
        measured.append(
            {
                "index": index,
                "matched": matched,
                "reference_center_mm": [center[0], center[1]],
                "reference_diameter_mm": diameter,
                "actual_center_mm": [actual_x, actual_y],
                "actual_diameter_mm": actual_radius * 2 if actual_radius is not None else None,
                "center_error_mm": center_error,
                "diameter_error_mm": diameter_error,
                "rim_vertex_count": len(rim),
            }
        )

    matched = [item for item in measured if item["matched"]]
    summary = {
        "side": side,
        "source": str(data_path.relative_to(ROOT)),
        "reference_hole_count": len(expected),
        "matched_hole_count": len(matched),
        "max_center_error_mm": max(item["center_error_mm"] for item in matched) if matched else None,
        "max_diameter_error_mm": max(item["diameter_error_mm"] for item in matched) if matched else None,
        "coordinate_transform": {
            "x_mm": "easyeda_x * 0.254 - 108.75",
            "y_mm": "91.8 - easyeda_y * 0.254",
            "anchors": "19 mm switch pitch and first-row switch centers",
        },
    }

    for folder in ("reference", "output", "overlay", "measurements"):
        (ARTIFACT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / f"reference/{side.lower()}-holes.json").write_text(
        json.dumps(
            [
                {"center_mm": list(center), "diameter_mm": diameter}
                for center, diameter in expected
            ],
            indent=2,
        )
    )
    (ARTIFACT_ROOT / f"output/{side.lower()}-mesh-rims.json").write_text(
        json.dumps(measured, indent=2)
    )
    (ARTIFACT_ROOT / f"measurements/{side.lower()}-summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    (ARTIFACT_ROOT / f"overlay/{side.lower()}-full.svg").write_text(
        svg_document(side, outline, expected, measured)
    )

    first_switch = expected[:4]
    crop_min_x = min(center[0] - diameter for center, diameter in first_switch) - 1
    crop_max_x = max(center[0] + diameter for center, diameter in first_switch) + 1
    crop_min_y = min(center[1] - diameter for center, diameter in first_switch) - 1
    crop_max_y = max(center[1] + diameter for center, diameter in first_switch) + 1
    (ARTIFACT_ROOT / f"overlay/{side.lower()}-first-switch-crop.svg").write_text(
        svg_document(
            side,
            outline,
            first_switch,
            measured[:4],
            crop=(crop_min_x, crop_min_y, crop_max_x, crop_max_y),
        )
    )
    return summary


if __name__ == "__main__":
    builder = load_builder_module()
    summaries = [verify_side(builder, side) for side in ("Left", "Right")]
    print("PCB_HOLE_VERIFY=" + json.dumps(summaries, sort_keys=True))
