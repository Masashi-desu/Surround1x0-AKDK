"""Render manufacturing views for the trackball sensor/case alignment."""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".tmp/mouse-sensor-alignment/output"
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
    scene.render.resolution_y = 800
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

    camera_data = bpy.data.cameras.new("Mouse_Sensor_Alignment_Camera_Data")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Mouse_Sensor_Alignment_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def aim(camera: bpy.types.Object, center: Vector, direction: Vector, scale: float) -> None:
    direction.normalize()
    camera.location = center + direction * 180
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale


def render(name: str) -> None:
    bpy.context.scene.render.filepath = str(OUTPUT / name)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    assembled_pose()
    camera = setup_scene()
    half = bpy.data.objects["Right_Half_Root"]
    case = bpy.data.objects["Right_Top_Case"]
    ball = bpy.data.objects["Right_Trackball_34mm"]
    sensor = bpy.data.objects["Right_Mouse_Sensor_Assembly"]
    case_objects = descendants(case)
    sensor_objects = descendants(sensor)
    ball_objects = descendants(ball)

    for obj in case_objects:
        obj.color = (0.33, 0.36, 0.43, 1)
    for obj in sensor_objects:
        role = obj.get("component_role", "")
        if "lens" in role:
            obj.color = (0.12, 0.72, 1.0, 1)
        elif "fpc" in role:
            obj.color = (0.92, 0.76, 0.16, 1)
        else:
            obj.color = (0.05, 0.70, 0.34, 1)
    for obj in ball_objects:
        obj.color = (0.38, 0.025, 0.07, 1)

    center = half.matrix_world @ Vector((8.0, -31.5, 5.5))
    top = half.matrix_world.to_3x3() @ Vector((0, 0, 1))
    bottom = -top
    right = half.matrix_world.to_3x3() @ Vector((1, 0, 0))

    set_visible(case_objects)
    aim(camera, center, bottom, 58)
    render("top-case-underside-openings.png")

    set_visible(case_objects | sensor_objects | ball_objects)
    render("sensor-case-underside.png")

    set_visible(case_objects | sensor_objects)
    render("sensor-case-underside-no-ball.png")

    set_visible(case_objects | sensor_objects | ball_objects)
    aim(camera, center, top, 58)
    render("sensor-case-top.png")

    aim(camera, center, right, 52)
    render("sensor-case-right-side.png")
    print("MOUSE_SENSOR_ALIGNMENT_RENDERS", sorted(str(path) for path in OUTPUT.glob("*.png")))


if __name__ == "__main__":
    main()
