"""Align primary-source photographs over Blender validation renders."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / ".tmp/controller-sensor-model"
OUTPUT = ARTIFACT / "output"
OVERLAY = ARTIFACT / "overlay"
OVERLAY.mkdir(parents=True, exist_ok=True)


def green_bbox(image: Image.Image, *, minimum_area: int = 10_000) -> tuple[int, int, int, int]:
    rgb = image.convert("RGB")
    mask = Image.new("1", rgb.size)
    source = rgb.load()
    target = mask.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = source[x, y]
            target[x, y] = green > 55 and green > red * 1.18 and green > blue * 1.06
    box = mask.getbbox()
    if box is None or (box[2] - box[0]) * (box[3] - box[1]) < minimum_area:
        raise RuntimeError("Could not find green PCB silhouette")
    return box


def photo_alpha(image: Image.Image, opacity: int) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _alpha = pixels[x, y]
            whiteness = min(red, green, blue)
            spread = max(red, green, blue) - min(red, green, blue)
            alpha = 0 if whiteness > 225 and spread < 24 else opacity
            pixels[x, y] = (red, green, blue, alpha)
    return rgba


def controller_overlay() -> None:
    render = Image.open(OUTPUT / "controller-left-top.png").convert("RGBA")
    reference = Image.open(
        ARTIFACT / "reference/repos/auto-kdk/img/wireless-controller-cut.png"
    ).convert("RGB")
    # The official red cut lines define the final top controller board.
    reference = reference.crop((151, 33, 891, 282))
    target = green_bbox(render)
    fitted = reference.resize((target[2] - target[0], target[3] - target[1]), Image.Resampling.LANCZOS)
    fitted = ImageEnhance.Contrast(fitted).enhance(1.08)
    layer = Image.new("RGBA", render.size)
    layer.alpha_composite(photo_alpha(fitted, 108), (target[0], target[1]))
    result = Image.alpha_composite(render, layer)
    draw = ImageDraw.Draw(result)
    draw.rectangle(target, outline=(40, 209, 124, 255), width=2)
    draw.text((22, 20), "Auto-KDK reference photo / Blender render overlay", fill=(255, 255, 255, 255))
    result.save(OVERLAY / "controller-photo-overlay.png")


def sensor_overlay() -> None:
    render = Image.open(OUTPUT / "sensor-module-top.png").convert("RGBA")
    reference = Image.open(
        ARTIFACT / "reference/repos/small-mouse-sensor-module/img/image.png"
    ).convert("RGB")
    # Official module photograph, cropped to its PCB silhouette.
    reference = reference.crop((112, 50, 305, 357))
    # The validation camera views the module from the ball-facing side, which
    # reverses the board's in-plane orientation relative to the bench photo.
    reference = reference.rotate(180)
    target = green_bbox(render, minimum_area=5_000)
    fitted = reference.resize((target[2] - target[0], target[3] - target[1]), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", render.size)
    layer.alpha_composite(photo_alpha(fitted, 104), (target[0], target[1]))
    result = Image.alpha_composite(render, layer)
    draw = ImageDraw.Draw(result)
    draw.rectangle(target, outline=(40, 209, 124, 255), width=2)
    draw.text((22, 20), "Mouse sensor reference photo / Blender render overlay", fill=(255, 255, 255, 255))
    result.save(OVERLAY / "sensor-photo-overlay.png")


if __name__ == "__main__":
    controller_overlay()
    sensor_overlay()
    print(
        "CONTROLLER_SENSOR_OVERLAYS",
        sorted(str(path) for path in OVERLAY.glob("*-photo-overlay.png")),
    )
