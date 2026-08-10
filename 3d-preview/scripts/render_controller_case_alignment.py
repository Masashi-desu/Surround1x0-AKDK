"""Render case openings and controller placement from manufacturing views."""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".tmp/controller-bottom-reference/output"
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


def setup_scene() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 760
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

    camera_data = bpy.data.cameras.new("Case_Alignment_Camera_Data")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Case_Alignment_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


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
    side = "Right"
    half = bpy.data.objects[f"{side}_Half_Root"]
    case = bpy.data.objects[f"{side}_Bottom_Case"]
    controller = bpy.data.objects[f"{side}_Controller_Assembly"]
    conthrough = bpy.data.objects[f"{side}_Conthrough_Assembly"]
    pcb = bpy.data.objects[f"{side}_PCB_Assembly"]
    case_objects = descendants(case)
    controller_objects = descendants(controller) | descendants(conthrough)
    assembly_objects = controller_objects | descendants(pcb)
    for obj in case_objects:
        obj.color = (0.28, 0.32, 0.39, 1)
    for obj in assembly_objects:
        family = obj.get("component_family")
        if family == "controller":
            obj.color = (0.03, 0.53, 0.30, 1)
        elif family == "conthrough":
            obj.color = (0.88, 0.52, 0.10, 1)
        elif obj.get("pcb_generated") is True:
            obj.color = (0.03, 0.18, 0.14, 1)
        else:
            obj.color = (0.62, 0.66, 0.73, 1)
    case_center_local = Vector((0, -1.8, -9.0))
    case_center = half.matrix_world @ case_center_local

    set_visible(case_objects)
    aim(camera, case_center, half.matrix_world.to_3x3() @ Vector((0, 0, 1)), 142)
    render("right-case-interior-top.png")

    aim(camera, case_center, half.matrix_world.to_3x3() @ Vector((0, 0, -1)), 142)
    render("right-case-exterior-bottom.png")

    side_center = half.matrix_world @ Vector((15, 51.5, -8.4))
    aim(camera, side_center, half.matrix_world.to_3x3() @ Vector((0, 1, 0)), 128)
    render("right-case-usb-side.png")

    set_visible(assembly_objects)
    aim(camera, side_center, half.matrix_world.to_3x3() @ Vector((0, 1, 0)), 128)
    render("right-controller-usb-side.png")

    set_visible(case_objects | assembly_objects)
    render("right-case-controller-assembled-usb-side.png")

    aim(camera, case_center, half.matrix_world.to_3x3() @ Vector((0, 0, -1)), 142)
    render("right-controller-bottom.png")

    set_visible(controller_objects)
    aim(camera, case_center, half.matrix_world.to_3x3() @ Vector((0, 0, -1)), 142)
    render("right-controller-only-bottom.png")
    print("CONTROLLER_CASE_ALIGNMENT_RENDERS", sorted(str(path) for path in OUTPUT.glob("*.png")))


if __name__ == "__main__":
    main()
