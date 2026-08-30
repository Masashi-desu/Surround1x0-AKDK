"""Render the generated USB-C receptacle from the front for reference QA."""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".tmp/usb-c-reference/output"
OUTPUT.mkdir(parents=True, exist_ok=True)


def assembled_pose() -> None:
    root = bpy.data.objects.get("Keyboard_Root")
    if root is not None:
        root["exploded_view_enabled"] = False
    for obj in bpy.data.objects:
        if obj.type != "EMPTY" or obj.get("exploded_view_order") is None:
            continue
        if obj.animation_data is not None:
            for driver in obj.animation_data.drivers:
                if driver.data_path == "location" and driver.array_index == 2:
                    driver.mute = True
        obj.location.z = 0
    bpy.context.view_layer.update()


def descendants(root: bpy.types.Object) -> set[bpy.types.Object]:
    result = {root}
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.add(obj)
        stack.extend(obj.children)
    return result


def renderables() -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT"}]


def set_visible(visible: set[bpy.types.Object]) -> None:
    for obj in renderables():
        obj.hide_render = obj not in visible


def setup_scene() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.008, 0.012, 0.020)

    camera_data = bpy.data.cameras.new("USB_C_Reference_Camera_Data")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("USB_C_Reference_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def aim_front(
    camera: bpy.types.Object,
    center: Vector,
    direction: Vector,
    scale: float,
) -> None:
    direction.normalize()
    camera.location = center + direction * 120
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale


def render(name: str) -> None:
    bpy.context.scene.render.filepath = str(OUTPUT / name)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    assembled_pose()
    camera = setup_scene()
    side = "Right"
    half = bpy.data.objects[f"{side}_Half_Root"]
    case = bpy.data.objects[f"{side}_Bottom_Case"]
    usb_parts = {
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(f"{side}_Controller_USB_C")
    }
    if len(usb_parts) != 5:
        raise RuntimeError(f"Expected five generated USB-C objects, found {sorted(obj.name for obj in usb_parts)}")

    case_objects = descendants(case)
    for obj in case_objects:
        obj.color = (0.52, 0.56, 0.62, 1)
    part_colors = {
        "outer_shell": (0.62, 0.66, 0.72, 1),
        "shell_mouth": (0.78, 0.82, 0.88, 1),
        "receptacle_cavity": (0.006, 0.009, 0.014, 1),
        "center_tongue": (0.025, 0.032, 0.040, 1),
        "signal_contacts": (0.72, 0.40, 0.10, 1),
    }
    for obj in usb_parts:
        obj.color = part_colors[obj.get("usb_c_part")]

    shell = bpy.data.objects[f"{side}_Controller_USB_C"]
    shell_points = [shell.matrix_world @ Vector(corner) for corner in shell.bound_box]
    center = Vector(
        tuple(
            (min(point[index] for point in shell_points) + max(point[index] for point in shell_points)) / 2
            for index in range(3)
        )
    )
    direction = half.matrix_world.to_3x3() @ Vector((0, 1, 0))
    aim_front(camera, center, direction, 10.0)

    set_visible(usb_parts)
    render("usb-c-front-model.png")

    set_visible(case_objects | usb_parts)
    render("usb-c-front-in-case.png")

    for obj in usb_parts:
        obj.color = (0.95, 0.95, 0.95, 1)
    set_visible(usb_parts)
    render("usb-c-front-silhouette.png")
    print("USB_C_REFERENCE_RENDERS", sorted(str(path) for path in OUTPUT.glob("*.png")))


if __name__ == "__main__":
    main()
