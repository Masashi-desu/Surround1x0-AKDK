"""Export the keyboard model as an assembled, metadata-rich GLB for /site."""

from __future__ import annotations

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "site/public/models/surround1x0-akdk.glb"


keyboard_collection = bpy.data.collections.get("Keyboard_Model")
if keyboard_collection is None:
    raise RuntimeError("Keyboard_Model collection was not found")

keyboard_root = bpy.data.objects.get("Keyboard_Root")
if keyboard_root is not None:
    # Layer Z locations are driver-controlled in the authoring blend. Disable
    # the display mode in this unsaved background session before exporting.
    keyboard_root["exploded_view_enabled"] = False
    keyboard_root["site_export_version"] = 1
    keyboard_root["site_exploded_spacing_mm"] = float(
        keyboard_root.get("exploded_view_spacing_mm", 30.0)
    )
bpy.context.view_layer.update()

# The live blend may currently show its exploded mode. Export the neutral pose;
# the layer name/order extras let Three.js reproduce any exploded amount.
layer_count = 0
for obj in keyboard_collection.all_objects:
    if (
        obj.type == "EMPTY"
        and obj.get("exploded_view_layer") is not None
        and obj.get("exploded_view_order") is not None
    ):
        if obj.animation_data is not None:
            for fcurve in obj.animation_data.drivers:
                if fcurve.data_path == "location" and fcurve.array_index == 2:
                    fcurve.mute = True
        obj.location.z = 0.0
        obj["site_assembled_location"] = tuple(obj.location)
        layer_count += 1

bpy.context.view_layer.update()
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")

export_objects = list(keyboard_collection.all_objects)
for obj in export_objects:
    if obj.name in bpy.context.view_layer.objects:
        obj.select_set(True)

if keyboard_root is not None:
    bpy.context.view_layer.objects.active = keyboard_root

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

candidates = {
    "filepath": str(OUTPUT),
    "check_existing": False,
    "export_format": "GLB",
    "use_selection": True,
    "export_extras": True,
    "export_yup": False,
    "export_apply": False,
    "export_animations": False,
    "export_cameras": False,
    "export_lights": False,
    "export_materials": "EXPORT",
    "export_image_format": "AUTO",
    "export_texcoords": True,
    "export_normals": True,
    "export_tangents": False,
    "export_attributes": True,
}
supported = {
    prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties
}
kwargs = {key: value for key, value in candidates.items() if key in supported}
result = bpy.ops.export_scene.gltf(**kwargs)
if "FINISHED" not in result:
    raise RuntimeError(f"GLB export failed: {result}")

print(
    "WEB_GLB_EXPORT",
    {
        "output": str(OUTPUT),
        "objects": len(export_objects),
        "exploded_layer_roots": layer_count,
        "layer_z_values": sorted(
            {
                round(float(obj.location.z), 6)
                for obj in keyboard_collection.all_objects
                if obj.type == "EMPTY"
                and obj.get("exploded_view_order") is not None
            }
        ),
        "bytes": OUTPUT.stat().st_size,
        "kwargs": sorted(kwargs),
    },
)
