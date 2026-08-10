"""Create reproducible reference/current comparisons for mouse-sensor placement."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageFont, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / ".tmp/mouse-sensor-alignment"
REFERENCE = ARTIFACT / "reference"
OUTPUT = ARTIFACT / "output"
OVERLAY = ARTIFACT / "overlay"
MEASUREMENTS = ARTIFACT / "measurements"
SUMMARY = ROOT / ".tmp/controller-sensor-model/measurements/controller-sensor-summary.json"


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    result = image.copy()
    result.thumbnail(size, Image.Resampling.LANCZOS)
    return result


def underside_overlay() -> tuple[Image.Image, dict]:
    reference = Image.open(REFERENCE / "underside-reference.png").convert("RGBA")
    current = Image.open(OUTPUT / "sensor-case-underside-no-ball.png").convert("RGBA")

    # The browser reference is a perspective view while the Blender evidence is
    # orthographic.  Align the trackball aperture as an ellipse; this explicit
    # affine normalization is used only for visual comparison, never to alter
    # model geometry.
    reference_anchor = {"center_px": [456.0, 536.0], "radius_px": [228.0, 205.0]}
    current_anchor = {"center_px": [683.5, 435.0], "radius_px": [270.5, 252.0]}
    scale_x = reference_anchor["radius_px"][0] / current_anchor["radius_px"][0]
    scale_y = reference_anchor["radius_px"][1] / current_anchor["radius_px"][1]
    resized = current.resize(
        (round(current.width * scale_x), round(current.height * scale_y)),
        Image.Resampling.LANCZOS,
    )
    translated_center = (
        current_anchor["center_px"][0] * scale_x,
        current_anchor["center_px"][1] * scale_y,
    )
    offset = (
        round(reference_anchor["center_px"][0] - translated_center[0]),
        round(reference_anchor["center_px"][1] - translated_center[1]),
    )

    gray = resized.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Contrast(edges).enhance(3.2)
    edges = edges.point(lambda value: 255 if value > 38 else 0)
    tint = Image.new("RGBA", resized.size, (37, 244, 139, 0))
    tint.putalpha(edges.point(lambda value: 205 if value else 0))
    overlay = reference.copy()
    overlay.alpha_composite(tint, dest=offset)
    overlay.save(OVERLAY / "underside-trackball-aperture-overlay.png")
    return overlay, {
        "alignment": "affine ellipse normalization",
        "reference_anchor": reference_anchor,
        "current_anchor": current_anchor,
        "scale_xy": [scale_x, scale_y],
        "translation_px": list(offset),
    }


def main() -> None:
    OVERLAY.mkdir(parents=True, exist_ok=True)
    MEASUREMENTS.mkdir(parents=True, exist_ok=True)
    summary = json.loads(SUMMARY.read_text())
    sensor = summary["sensor"]
    overlay, transform = underside_overlay()

    external = fit(Image.open(REFERENCE / "external-before.png").convert("RGB"), (780, 620))
    current_top = fit(Image.open(OUTPUT / "sensor-case-top.png").convert("RGB"), (780, 620))
    underside_ref = fit(Image.open(REFERENCE / "underside-reference.png").convert("RGB"), (780, 720))
    underside_mix = fit(overlay.convert("RGB"), (780, 720))

    canvas = Image.new("RGB", (1640, 1510), (11, 16, 24))
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.load_default(size=22)
    label_font = ImageFont.load_default(size=17)
    small_font = ImageFont.load_default(size=15)
    draw.text((30, 18), "TRACKBALL SENSOR - reference / corrected model", fill="white", font=title_font)

    canvas.paste(external, (30, 65))
    canvas.paste(current_top, (830, 65))
    draw.text((30, 42), "BEFORE: PCB exposed at ball front", fill=(255, 145, 158), font=label_font)
    draw.text((830, 42), "CURRENT: sensor hidden in +X case pocket", fill=(82, 240, 159), font=label_font)

    bottom_y = 690
    canvas.paste(underside_ref, (30, bottom_y))
    canvas.paste(underside_mix, (830, bottom_y))
    draw.text((30, bottom_y - 24), "UNDERSIDE REFERENCE", fill="white", font=label_font)
    draw.text((830, bottom_y - 24), "GREEN EDGE: current render aligned by trackball aperture", fill="white", font=label_font)
    draw.text(
        (30, 1465),
        (
            f"lens residual {sensor['lens_target_error_mm']:.6f} mm  |  "
            f"axis residual {sensor['optical_axis_angle_error_deg']:.3f} deg  |  "
            f"ball clearance {sensor['lens_to_ball_surface_clearance_mm']:.3f} mm  |  "
            "FPC +Y toward Auto-KDK"
        ),
        fill=(188, 205, 226),
        font=small_font,
    )
    canvas.save(OVERLAY / "mouse-sensor-alignment-contact-sheet.png")

    result = {
        "revision": summary["revision"],
        "overlay_transform": transform,
        "lens_target_error_mm": sensor["lens_target_error_mm"],
        "optical_axis_angle_error_deg": sensor["optical_axis_angle_error_deg"],
        "lens_to_ball_surface_clearance_mm": sensor["lens_to_ball_surface_clearance_mm"],
        "fpc_connector_toward_autokdk": sensor["fpc_connector_toward_autokdk"],
        "fpc_escape_groove_y_mm": sensor["fpc_escape_groove_y_mm"],
    }
    (MEASUREMENTS / "mouse-sensor-alignment.json").write_text(json.dumps(result, indent=2))
    print(OVERLAY / "mouse-sensor-alignment-contact-sheet.png")


if __name__ == "__main__":
    main()
