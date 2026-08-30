"""Export assembled black/white preview GLBs and the black /site model."""

from __future__ import annotations

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
EXPORTS = (
    ("black", ROOT / "3d-preview/Surround1x0-AKDK-Black.glb"),
    ("white", ROOT / "3d-preview/Surround1x0-AKDK-White.glb"),
    ("black", ROOT / "site/public/models/surround1x0-akdk.glb"),
)

COLORWAYS = {
    "black": {
        "Case_Warm_Ivory_Print": (0.015, 0.018, 0.023, 1.0),
        "Keycap_Warm_Ivory_PBT": (0.025, 0.030, 0.038, 1.0),
        "Keycap_Cool_Gray_Accent": (0.025, 0.030, 0.038, 1.0),
        "Keycap_High_Homing_Bar_Contrast": (0.94, 0.947, 0.956, 1.0),
        "Keycap_Low_Homing_Bar_Contrast": (0.94, 0.947, 0.956, 1.0),
        "Trackball_Gunmetal": (0.168269, 0.028426, 0.038204, 1.0),
    },
    "white": {
        "Case_Warm_Ivory_Print": (0.72, 0.65, 0.50, 1.0),
        "Keycap_Warm_Ivory_PBT": (0.84, 0.79, 0.70, 1.0),
        "Keycap_Cool_Gray_Accent": (0.34, 0.36, 0.38, 1.0),
        "Keycap_High_Homing_Bar_Contrast": (0.34, 0.36, 0.38, 1.0),
        "Keycap_Low_Homing_Bar_Contrast": (0.84, 0.79, 0.70, 1.0),
        "Trackball_Gunmetal": (0.34, 0.36, 0.38, 1.0),
    },
}


def required_material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        if "Homing_Bar_Contrast" in name:
            raise RuntimeError(
                "Required homing-bar material is missing from the Blender model: "
                f"{name}"
            )
        raise RuntimeError(f"Required colorway material was not found: {name}")
    return material


def set_material_color(
    material: bpy.types.Material,
    rgba: tuple[float, float, float, float],
) -> None:
    material.diffuse_color = rgba
    if material.use_nodes:
        principled = next(
            (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
            None,
        )
        if principled is None:
            raise RuntimeError(f"Principled BSDF node missing from {material.name}")
        principled.inputs["Base Color"].default_value = rgba


base_materials = {name: required_material(name) for name in COLORWAYS["black"]}
white_materials: dict[str, bpy.types.Material] = {}


def ensure_white_materials() -> dict[str, bpy.types.Material]:
    if white_materials:
        return white_materials
    for name, material in base_materials.items():
        copy = bpy.data.materials.new(f"{name}_White_Colorway")
        copy.use_nodes = True
        source_principled = next(
            (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
            None,
        )
        target_principled = next(
            (node for node in copy.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
            None,
        )
        if source_principled is None or target_principled is None:
            raise RuntimeError(f"Principled BSDF node missing while copying {name}")
        for target_input in target_principled.inputs:
            source_input = source_principled.inputs.get(target_input.identifier)
            if source_input is not None and hasattr(target_input, "default_value"):
                try:
                    target_input.default_value = source_input.default_value
                except (TypeError, ValueError):
                    pass
        copy["temporary_export_material"] = True
        set_material_color(copy, COLORWAYS["white"][name])
        white_materials[name] = copy
    return white_materials


def apply_colorway(name: str) -> dict[str, bpy.types.Material]:
    target_materials = base_materials if name == "black" else ensure_white_materials()
    reverse = {
        material.as_pointer(): base_name
        for base_name, material in base_materials.items()
    }
    reverse.update(
        {
            material.as_pointer(): base_name
            for base_name, material in white_materials.items()
        }
    )
    for obj in keyboard_collection.all_objects:
        for slot in obj.material_slots:
            material = slot.material
            if material is not None and material.as_pointer() in reverse:
                slot.material = target_materials[reverse[material.as_pointer()]]
    for material_name, material in target_materials.items():
        set_material_color(material, COLORWAYS[name][material_name])
    return target_materials


def cleanup_white_materials() -> None:
    apply_colorway("black")
    for material in list(white_materials.values()):
        bpy.data.materials.remove(material)
    white_materials.clear()


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

export_objects = [
    obj for obj in keyboard_collection.all_objects
    if not obj.name.startswith("Legend_")
]
for obj in export_objects:
    if obj.name in bpy.context.view_layer.objects:
        obj.select_set(True)

if keyboard_root is not None:
    bpy.context.view_layer.objects.active = keyboard_root

candidates = {
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
export_results = []
for colorway, output in EXPORTS:
    colorway_materials = apply_colorway(colorway)
    if keyboard_root is not None:
        keyboard_root["black_colorway"] = colorway == "black"
        keyboard_root["exported_colorway"] = colorway
    bpy.context.view_layer.update()

    output.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_scene.gltf(filepath=str(output), **kwargs)
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB export failed for {output}: {result}")
    export_results.append(
        {
            "colorway": colorway,
            "output": str(output),
            "bytes": output.stat().st_size,
            "materials": {
                name: {
                    "datablock": material.name,
                    "users": material.users,
                    "base_color": list(
                        next(
                            node for node in material.node_tree.nodes
                            if node.type == "BSDF_PRINCIPLED"
                        ).inputs["Base Color"].default_value
                    ),
                }
                for name, material in colorway_materials.items()
            },
        }
    )

cleanup_white_materials()

print(
    "WEB_GLB_EXPORT",
    {
        "outputs": export_results,
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
        "kwargs": sorted(kwargs),
    },
)
