"""Render isolated validation views for the controller and sensor assemblies."""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".tmp/controller-sensor-model/output"
OUTPUT.mkdir(parents=True, exist_ok=True)


def assembled_pose() -> None:
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


def setup_scene() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = scene.world or bpy.data.worlds.new("Validation_World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.007, 0.010, 0.016, 1)
    background.inputs["Strength"].default_value = 0.30

    camera_data = bpy.data.cameras.new("Validation_Camera_Data")
    camera = bpy.data.objects.new("Validation_Camera", camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    scene.camera = camera

    for name, energy, color, location in (
        ("Validation_Key", 1400, (1.0, 0.94, 0.86), (-90, -80, 130)),
        ("Validation_Fill", 950, (0.55, 0.72, 1.0), (90, 25, 100)),
        ("Validation_Rim", 700, (0.40, 0.56, 1.0), (0, 100, 60)),
    ):
        data = bpy.data.lights.new(f"{name}_Data", "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = 85
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
    return camera


def descendants(root: bpy.types.Object) -> set[bpy.types.Object]:
    result = {root}
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.add(obj)
        stack.extend(obj.children)
    return result


def all_renderables() -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT", "SURFACE", "META"}]


def set_visible(objects: set[bpy.types.Object]) -> None:
    for obj in all_renderables():
        obj.hide_render = obj not in objects


def bounds(objects: set[bpy.types.Object]) -> tuple[Vector, Vector]:
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "FONT", "SURFACE", "META"}:
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            for index in range(3):
                minimum[index] = min(minimum[index], point[index])
                maximum[index] = max(maximum[index], point[index])
    return minimum, maximum


def aim(camera: bpy.types.Object, center: Vector, direction: Vector, ortho_scale: float) -> None:
    direction.normalize()
    camera.location = center + direction * 150
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = ortho_scale


def render(name: str) -> None:
    bpy.context.scene.render.filepath = str(OUTPUT / name)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    assembled_pose()
    camera = setup_scene()

    left = bpy.data.objects["Left_Controller_Assembly"]
    left_objects = descendants(left)
    set_visible(left_objects)
    minimum, maximum = bounds(left_objects)
    center = (minimum + maximum) / 2
    normal = bpy.data.objects["Left_Half_Root"].matrix_world.to_3x3() @ Vector((0, 0, 1))
    aim(camera, center, normal, 104)
    render("controller-left-top.png")

    conthrough = descendants(bpy.data.objects["Left_Conthrough_Assembly"])
    controller_and_pins = left_objects | conthrough
    set_visible(controller_and_pins)
    minimum, maximum = bounds(controller_and_pins)
    center = (minimum + maximum) / 2
    local_direction = Vector((-0.35, -1.0, 0.32)).normalized()
    direction = bpy.data.objects["Left_Half_Root"].matrix_world.to_3x3() @ local_direction
    aim(camera, center, direction, 103)
    render("controller-conthrough-side.png")

    sensor_root = bpy.data.objects["Right_Mouse_Sensor_Assembly"]
    sensor_objects = {
        obj for obj in descendants(sensor_root)
        if obj.name != "Right_Mouse_Sensor_FPC_Ribbon"
    }
    set_visible(sensor_objects)
    sensor_board = bpy.data.objects["Right_Mouse_Sensor_PCB"]
    center = sensor_board.matrix_world.translation.copy()
    normal = sensor_board.matrix_world.to_3x3() @ Vector((0, 0, 1))
    aim(camera, center, normal, 22)
    render("sensor-module-top.png")

    electronics = set()
    for obj in all_renderables():
        current = obj
        layer = None
        while current is not None:
            if current.get("exploded_view_layer") is not None:
                layer = current.get("exploded_view_layer")
                break
            current = current.parent
        if layer in {"pcb", "sockets", "conthrough", "controller", "mouse_sensor"}:
            electronics.add(obj)
    set_visible(electronics)
    minimum, maximum = bounds(electronics)
    center = (minimum + maximum) / 2
    aim(camera, center, Vector((0.68, -0.92, 0.78)), 285)
    render("electronics-assembled.png")
    print("CONTROLLER_SENSOR_RENDERS", sorted(str(path) for path in OUTPUT.glob("*.png")))


if __name__ == "__main__":
    main()
