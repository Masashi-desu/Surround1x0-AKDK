"""Create source-derived case/controller overlays from the latest renders."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".tmp/controller-bottom-reference/output"
MEASUREMENTS = ROOT / ".tmp/controller-sensor-model/measurements/controller-sensor-summary.json"


def foreground_mask(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    difference = ImageChops.difference(rgb, background).convert("L")
    difference = ImageEnhance.Contrast(difference).enhance(2.8)
    return difference.point(lambda value: 255 if value > 16 else 0).filter(ImageFilter.MaxFilter(3))


def overlay_pair(case_name: str, assembly_name: str, output_name: str) -> Image.Image:
    case = Image.open(OUTPUT / case_name).convert("RGBA")
    assembly = Image.open(OUTPUT / assembly_name).convert("RGBA")
    mask = foreground_mask(assembly)
    tint = Image.new("RGBA", assembly.size, (28, 226, 139, 0))
    tint.putalpha(mask.point(lambda value: 142 if value else 0))
    composite = Image.alpha_composite(case, tint)

    edge = mask.filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value > 24 else 0)
    outline = Image.new("RGBA", assembly.size, (255, 67, 126, 0))
    outline.putalpha(edge)
    composite = Image.alpha_composite(composite, outline)
    composite.save(OUTPUT / output_name)
    return composite


def main() -> None:
    summary = json.loads(MEASUREMENTS.read_text())
    alignment = summary["case_alignment"]
    side = overlay_pair(
        "right-case-usb-side.png",
        "right-controller-usb-side.png",
        "overlay-right-usb-case-controller.png",
    )
    bottom = overlay_pair(
        "right-case-exterior-bottom.png",
        "right-controller-only-bottom.png",
        "overlay-right-bottom-case-controller.png",
    )

    canvas = Image.new("RGB", (1200, 1600), (13, 18, 27))
    canvas.paste(side.convert("RGB"), (0, 0))
    canvas.paste(bottom.crop((0, 0, 1200, 760)).convert("RGB"), (0, 800))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)
    small = ImageFont.load_default(size=16)
    draw.rectangle((0, 0, 1200, 48), fill=(8, 12, 19))
    draw.text((24, 13), "SIDE USB APERTURE — case reference + controller overlay", fill=(245, 247, 250), font=font)
    draw.rectangle((0, 760, 1200, 840), fill=(8, 12, 19))
    draw.text((24, 774), "BOTTOM SWITCH SLOT — case reference + controller overlay", fill=(245, 247, 250), font=font)
    draw.text(
        (24, 806),
        (
            f"conthrough residual {alignment['maximum_conthrough_pin_to_easyeda_error_mm']:.5f} mm   |   "
            f"USB aperture clearance {alignment['minimum_usb_aperture_clearance_xz_mm']:.2f} mm   |   "
            f"PCB wall recess {alignment['minimum_pcb_case_wall_recess_mm']:.2f} mm   |   "
            f"switch XY residual {alignment['maximum_power_slot_xy_error_mm']:.5f} mm   |   "
            f"battery/support residual {alignment['maximum_battery_support_residual_mm']:.2f} mm"
        ),
        fill=(182, 198, 218),
        font=small,
    )
    canvas.save(OUTPUT / "controller-case-alignment-contact-sheet.png")
    print(OUTPUT / "controller-case-alignment-contact-sheet.png")


if __name__ == "__main__":
    main()
