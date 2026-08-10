"""Add a reversible, assembly-level exploded-view display mode.

The switch internals remain untouched.  Only display-layer roots are moved, so
the original assembled transforms are restored exactly when the mode is off.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Matrix


REVISION = "assembly-exploded-view-v5-bottom-controller"
DEFAULT_SPACING_MM = 30.0

KEYBOARD_ROOT = "Keyboard_Root"
HALF_ROOTS = {
    "Left": "Left_Half_Root",
    "Right": "Right_Half_Root",
}

LAYER_DEFINITIONS = (
    ("bottom_case", "Bottom Case", 0),
    ("controller", "Auto-KDK Controller", 1),
    ("mouse_sensor", "Mouse Sensor + FPC", 1),
    ("conthrough", "Conthrough Pins", 2),
    ("sockets", "Hot-swap Sockets", 2),
    ("pcb", "PCB", 3),
    ("top_case", "Top Case", 4),
    ("switches", "Switches", 5),
    ("keycaps", "Keycaps + Legends", 6),
    ("trackball", "Trackball", 7),
)


def find_half_side(obj: bpy.types.Object) -> str | None:
    """Return the half name for an object anywhere below a half root."""
    current = obj
    while current is not None:
        for side, root_name in HALF_ROOTS.items():
            if current.name == root_name:
                return side
        current = current.parent
    return None


def ensure_control_properties(root: bpy.types.Object, enabled: bool, spacing_mm: float) -> None:
    root["exploded_view_enabled"] = bool(enabled)
    root["exploded_view_spacing_mm"] = float(spacing_mm)
    root["exploded_view_revision"] = REVISION
    root["exploded_view_order"] = (
        "Bottom case > Auto-KDK + mouse sensor > Conthrough + hot-swap sockets > PCB > "
        "Top case > Switches > Keycaps > Trackball"
    )
    root["exploded_view_note"] = (
        "Assembly-level display mode. Choc V2 internal components stay assembled."
    )

    root.id_properties_ui("exploded_view_enabled").update(
        default=False,
        description="Separate the main keyboard assemblies vertically",
    )
    root.id_properties_ui("exploded_view_spacing_mm").update(
        default=DEFAULT_SPACING_MM,
        min=5.0,
        max=100.0,
        soft_min=15.0,
        soft_max=60.0,
        precision=1,
        description="Vertical distance between exploded-view layers (model millimetres)",
    )


def layer_root_name(side: str, layer_key: str) -> str:
    return f"{side}_Exploded_Layer_{layer_key}"


def ensure_layer_root(
    side: str,
    half_root: bpy.types.Object,
    layer_key: str,
    label: str,
    order: int,
    keyboard_root: bpy.types.Object,
) -> bpy.types.Object:
    name = layer_root_name(side, layer_key)
    layer_root = bpy.data.objects.get(name)
    if layer_root is None:
        layer_root = bpy.data.objects.new(name, None)
        target_collection = half_root.users_collection[0] if half_root.users_collection else bpy.context.scene.collection
        target_collection.objects.link(layer_root)
    elif layer_root.type != "EMPTY":
        raise RuntimeError(f"Expected {name} to be an Empty, found {layer_root.type}")

    try:
        layer_root.driver_remove("location", 2)
    except (TypeError, RuntimeError):
        pass

    layer_root.parent = half_root
    layer_root.matrix_parent_inverse = Matrix.Identity(4)
    layer_root.matrix_basis = Matrix.Identity(4)
    layer_root.empty_display_type = "PLAIN_AXES"
    layer_root.empty_display_size = 0.01
    layer_root.hide_render = True
    layer_root.show_name = False
    layer_root["exploded_view_layer"] = layer_key
    layer_root["exploded_view_label"] = label
    layer_root["exploded_view_order"] = order
    layer_root["exploded_view_revision"] = REVISION

    fcurve = layer_root.driver_add("location", 2)
    driver = fcurve.driver
    driver.type = "SCRIPTED"

    enabled_var = driver.variables.new()
    enabled_var.name = "enabled"
    enabled_var.type = "SINGLE_PROP"
    enabled_var.targets[0].id = keyboard_root
    enabled_var.targets[0].data_path = '["exploded_view_enabled"]'

    spacing_var = driver.variables.new()
    spacing_var.name = "spacing"
    spacing_var.type = "SINGLE_PROP"
    spacing_var.targets[0].id = keyboard_root
    spacing_var.targets[0].data_path = '["exploded_view_spacing_mm"]'

    driver.expression = f"enabled * spacing * {order}"
    return layer_root


def classify_objects() -> dict[tuple[str, str], list[bpy.types.Object]]:
    assignments: dict[tuple[str, str], list[bpy.types.Object]] = {}

    def add(side: str | None, layer: str, obj: bpy.types.Object) -> None:
        if side is None:
            raise RuntimeError(f"Could not determine keyboard half for {obj.name}")
        assignments.setdefault((side, layer), []).append(obj)

    exact_layers = {
        "Left_Bottom_Case": ("Left", "bottom_case"),
        "Left_Top_Case": ("Left", "top_case"),
        "Right_Bottom_Case": ("Right", "bottom_case"),
        "Right_Top_Case": ("Right", "top_case"),
        "Right_Trackball_34mm": ("Right", "trackball"),
    }
    for name, (side, layer) in exact_layers.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(f"Required exploded-view object is missing: {name}")
        add(side, layer, obj)

    for obj in bpy.data.objects:
        if obj.get("socket_assembly") is True:
            add(find_half_side(obj), "sockets", obj)
        elif obj.get("pcb_assembly") is True:
            add(find_half_side(obj), "pcb", obj)
        elif obj.get("conthrough_assembly") is True:
            add(find_half_side(obj), "conthrough", obj)
        elif obj.get("controller_assembly") is True:
            add(find_half_side(obj), "controller", obj)
        elif obj.get("mouse_sensor_assembly") is True:
            add(find_half_side(obj), "mouse_sensor", obj)
        elif obj.get("switch_type") == "Kailh Choc V2 (PG1353)":
            add(find_half_side(obj), "switches", obj)
        elif obj.name.startswith(("Left_Keycap_", "Right_Keycap_")):
            add(find_half_side(obj), "keycaps", obj)
        elif obj.name.startswith("Legend_"):
            add(find_half_side(obj), "keycaps", obj)

    return assignments


def reparent_preserving_world(obj: bpy.types.Object, new_parent: bpy.types.Object) -> None:
    if obj.parent == new_parent:
        return
    world_matrix = obj.matrix_world.copy()
    parent_inverse_world = new_parent.matrix_world.inverted_safe()
    obj.parent = new_parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = parent_inverse_world @ world_matrix


def refresh_drivers(keyboard_root: bpy.types.Object) -> None:
    """Force scripted-driver evaluation in background and interactive Blender."""
    keyboard_root.update_tag(refresh={"OBJECT"})
    scene = bpy.context.scene
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()


def validate_assignments(assignments: dict[tuple[str, str], list[bpy.types.Object]]) -> None:
    expected = {
        "bottom_case": 2,
        "sockets": 2,
        "pcb": 2,
        "conthrough": 2,
        "controller": 2,
        "mouse_sensor": 1,
        "top_case": 2,
        "switches": 45,
        "keycaps": 90,
        "trackball": 1,
    }
    actual = {
        layer: sum(len(objects) for (side, key), objects in assignments.items() if key == layer)
        for layer in expected
    }
    if actual != expected:
        raise RuntimeError(f"Exploded-view component counts do not match: expected={expected}, actual={actual}")


def setup_exploded_view(enabled: bool = True, spacing_mm: float = DEFAULT_SPACING_MM) -> dict:
    keyboard_root = bpy.data.objects.get(KEYBOARD_ROOT)
    if keyboard_root is None:
        raise RuntimeError(f"Missing required object: {KEYBOARD_ROOT}")

    half_roots = {side: bpy.data.objects.get(name) for side, name in HALF_ROOTS.items()}
    missing_halves = [name for side, name in HALF_ROOTS.items() if half_roots[side] is None]
    if missing_halves:
        raise RuntimeError(f"Missing half roots: {missing_halves}")

    assignments = classify_objects()
    validate_assignments(assignments)
    # Build and reparent at the assembled position.  Enabling the drivers before
    # reparenting would bake the layer offsets into every child's local matrix.
    ensure_control_properties(keyboard_root, enabled=False, spacing_mm=spacing_mm)
    refresh_drivers(keyboard_root)

    layer_roots: dict[tuple[str, str], bpy.types.Object] = {}
    for side, half_root in half_roots.items():
        for layer_key, label, order in LAYER_DEFINITIONS:
            if side == "Left" and layer_key in {"trackball", "mouse_sensor"}:
                continue
            layer_roots[(side, layer_key)] = ensure_layer_root(
                side=side,
                half_root=half_root,
                layer_key=layer_key,
                label=label,
                order=order,
                keyboard_root=keyboard_root,
            )

    # The new layer roots must have evaluated world matrices before child local
    # matrices are calculated from them.
    refresh_drivers(keyboard_root)

    for key, objects in assignments.items():
        target = layer_roots[key]
        for obj in objects:
            reparent_preserving_world(obj, target)
            obj["exploded_view_layer"] = key[1]

    keyboard_root["exploded_view_enabled"] = bool(enabled)
    keyboard_root["exploded_view_layer_root_count"] = len(layer_roots)
    keyboard_root["exploded_view_component_count"] = sum(len(v) for v in assignments.values())
    refresh_drivers(keyboard_root)

    counts = {
        layer: sum(len(objects) for (side, key), objects in assignments.items() if key == layer)
        for layer, _label, _order in LAYER_DEFINITIONS
    }
    return {
        "revision": REVISION,
        "enabled": bool(keyboard_root["exploded_view_enabled"]),
        "spacing_mm": float(keyboard_root["exploded_view_spacing_mm"]),
        "layer_root_count": len(layer_roots),
        "component_counts": counts,
        "layer_offsets_mm": {
            key: order * spacing_mm for key, _label, order in LAYER_DEFINITIONS
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--spacing", type=float, default=DEFAULT_SPACING_MM)
    parser.add_argument("--assembled", action="store_true", help="Save with exploded view disabled")
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    result = setup_exploded_view(enabled=not args.assembled, spacing_mm=args.spacing)
    output = args.output.resolve() if args.output else Path(bpy.data.filepath).resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    result["output"] = str(output)
    print("EXPLODED_VIEW_RESULT=" + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
