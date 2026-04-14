#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = ROOT.name
KEYMAP_FILE = ROOT / "config" / "keymap.keymap"
LAYOUT_INFO_FILE = ROOT / "config" / "info.json"
KEYMAP_DRAWER_CONFIG = ROOT / "keymap-drawer" / "config.yaml"
OUTPUT_YAML = ROOT / "keymap-drawer" / f"{PROJECT_NAME}.yaml"
OUTPUT_SVG = ROOT / "images" / f"{PROJECT_NAME}-keymap.svg"
LAYOUT_SHIFT_MAP_FILE = ROOT / "src" / "layouts" / "layout_swap_ctrl_cmd.h"
LAYOUT_ENV_MAP_FILE = ROOT / "src" / "layouts" / "layout_jis.h"

LAYOUT_SHIFT_OFF_LABEL = "Mac"
LAYOUT_SHIFT_ON_LABEL = "Win"
LAYOUT_ENV_OFF_LABEL = "US"
LAYOUT_ENV_ON_LABEL = "JIS"

KEYCODE_ALIASES = {
    "LCTRL": "LEFT_CONTROL",
    "RCTRL": "RIGHT_CONTROL",
    "LALT": "LEFT_ALT",
    "RALT": "RIGHT_ALT",
    "LCMD": "LEFT_COMMAND",
    "RCMD": "RIGHT_COMMAND",
    "SQT": "SINGLE_QUOTE",
}

KEYCODE_LEGENDS = {
    "DELETE": "Del",
    "CAPSLOCK": "Caps",
    "LEFT_BRACKET": "[",
    "RIGHT_BRACKET": "]",
    "LEFT_BRACE": "{",
    "RIGHT_BRACE": "}",
    "LEFT_PARENTHESIS": "(",
    "RIGHT_PARENTHESIS": ")",
    "SEMICOLON": ";",
    "COLON": ":",
    "SINGLE_QUOTE": "'",
    "DOUBLE_QUOTES": '"',
    "GRAVE": "`",
    "BACKSLASH": "\\",
    "PIPE": "|",
    "SLASH": "/",
    "COMMA": ",",
    "PERIOD": ".",
    "MINUS": "-",
    "EQUAL": "=",
    "PLUS": "+",
    "ASTERISK": "*",
    "EXCLAMATION": "!",
    "UNDERSCORE": "_",
    "AT_SIGN": "@",
    "CARET": "^",
    "TILDE": "~",
    "AMPERSAND": "&",
    "PAGE_UP": "PgUp",
    "PAGE_DOWN": "PgDn",
    "UP_ARROW": "Up",
    "DOWN_ARROW": "Down",
    "LEFT_ARROW": "Left",
    "RIGHT_ARROW": "Right",
    "HOME": "Home",
    "END": "End",
    "SPACE": "Space",
    "TAB": "Tab",
    "ENTER": "Enter",
    "ESC": "Esc",
    "ESCAPE": "Esc",
    "LANG1": "Lang1",
    "LANG2": "Lang2",
    "LANGUAGE_1": "Lang1",
    "LANGUAGE_2": "Lang2",
    "SCRL_UP": "↑",
    "SCRL_DOWN": "↓",
    "SCRL_LEFT": "←",
    "SCRL_RIGHT": "→",
    "0x89": "¥",
    "LS(0x89)": "|",
    "0x87": "^",
    "LS(0x87)": "_",
}

MOUSE_BUTTON_LEGENDS = {
    "MB1": "L Click",
    "MB2": "R Click",
    "MB3": "Mid Click",
    "MB4": "Back",
    "MB5": "Fwd",
}


def load_layout_name() -> str:
    info = json.loads(LAYOUT_INFO_FILE.read_text())
    return next(iter(info["layouts"]))


def parse_array_entries(path: Path, array_name: str) -> list[tuple[str, ...]]:
    lines = path.read_text().splitlines()
    in_array = False
    entries: list[tuple[str, ...]] = []
    entry_re = re.compile(r"\{\s*([^,]+?)\s*,\s*([^,}]+?)(?:\s*,\s*([^,}]+?))?\s*\}")

    for raw_line in lines:
        line = raw_line.split("/*", 1)[0].strip()
        if not in_array:
            if f"{array_name}[]" in line and line.endswith("{"):
                in_array = True
            continue

        if line.startswith("};"):
            break
        if not line.startswith("{"):
            continue

        match = entry_re.search(line)
        if not match:
            continue

        entries.append(tuple(part for part in match.groups() if part is not None))

    if not entries:
        raise RuntimeError(f'No entries found for "{array_name}" in {path}')

    return entries


def normalize_keycode(keycode: str) -> str:
    return KEYCODE_ALIASES.get(keycode, keycode)


def keycode_legend(keycode: str, profile: str | None = None) -> str:
    normalized = normalize_keycode(keycode)
    if normalized in {"LEFT_CONTROL", "RIGHT_CONTROL"}:
        return "Ctrl"
    if normalized in {"LEFT_ALT", "RIGHT_ALT"}:
        return "Opt" if profile == "mac" else "Alt"
    if normalized in {"LEFT_COMMAND", "RIGHT_COMMAND"}:
        return "Cmd"
    if normalized in {"LEFT_GUI", "RIGHT_GUI"}:
        return "Win"
    if normalized in KEYCODE_LEGENDS:
        return KEYCODE_LEGENDS[normalized]

    number_match = re.fullmatch(r"(?:N(?:UM(?:BER)?)?_)?(\d)", normalized)
    if number_match:
        return number_match.group(1)

    if re.fullmatch(r"[A-Z]", normalized):
        return normalized

    return normalized.replace("_", " ").title()


def make_stateful_label(off: str, on: str) -> str:
    separator = " / " if max(len(off), len(on)) <= 2 else "/"
    return f"{off}{separator}{on}"


def stateful_key_label(keycode: str, mapping: dict[str, str], off_profile: str | None = None, on_profile: str | None = None) -> str:
    normalized = normalize_keycode(keycode)
    off_legend = keycode_legend(normalized, off_profile)
    if normalized not in mapping:
        return off_legend

    on_legend = keycode_legend(mapping[normalized], on_profile)
    if off_legend == on_legend:
        return off_legend

    return make_stateful_label(off_legend, on_legend)


def merge_layer_state_label(off_name: str, on_name: str) -> str:
    if off_name.endswith(LAYOUT_SHIFT_OFF_LABEL) and on_name.endswith(LAYOUT_SHIFT_ON_LABEL):
        off_root = off_name[: -len(LAYOUT_SHIFT_OFF_LABEL)]
        on_root = on_name[: -len(LAYOUT_SHIFT_ON_LABEL)]
        if off_root and off_root == on_root:
            return f"{off_root}\n{LAYOUT_SHIFT_OFF_LABEL}/{LAYOUT_SHIFT_ON_LABEL}"
    return f"{off_name}\n{on_name}"


def rewrite_binding(
    binding: str,
    layer_names: list[str],
    shift_key_map: dict[str, str],
    env_key_map: dict[str, str],
    scroll_map: dict[str, str],
    layer_map: dict[int, int],
) -> str:
    parts = binding.split()
    if not parts or not parts[0].startswith("&"):
        return binding

    match parts:
        case ["&kpls", keycode]:
            return stateful_key_label(keycode, shift_key_map, "mac", "win")
        case ["&kple", keycode]:
            return stateful_key_label(keycode, env_key_map)
        case ["&mscls", direction]:
            return stateful_key_label(direction, scroll_map)
        case ["&mols", layer]:
            base_layer = int(layer)
            shifted_layer = layer_map.get(base_layer, base_layer)
            return merge_layer_state_label(layer_names[base_layer], layer_names[shifted_layer])
        case ["&mkp", button]:
            return MOUSE_BUTTON_LEGENDS.get(button, button)
        case ["&studio_unlock"]:
            return "Studio"
        case ["&to_ls"] | ["&to_ls", "0"]:
            return LAYOUT_SHIFT_OFF_LABEL
        case ["&to_ls", "1"]:
            return LAYOUT_SHIFT_ON_LABEL
        case ["&tog_ls"]:
            return f"{LAYOUT_SHIFT_OFF_LABEL}/{LAYOUT_SHIFT_ON_LABEL}"
        case ["&to_le"] | ["&to_le", "0"]:
            return LAYOUT_ENV_OFF_LABEL
        case ["&to_le", "1"]:
            return LAYOUT_ENV_ON_LABEL
        case ["&tog_le"]:
            return f"{LAYOUT_ENV_OFF_LABEL}/{LAYOUT_ENV_ON_LABEL}"
        case _:
            return binding


def rewrite_key_spec(
    spec: Any,
    layer_names: list[str],
    shift_key_map: dict[str, str],
    env_key_map: dict[str, str],
    scroll_map: dict[str, str],
    layer_map: dict[int, int],
) -> Any:
    if isinstance(spec, str):
        return rewrite_binding(spec, layer_names, shift_key_map, env_key_map, scroll_map, layer_map)

    if isinstance(spec, dict):
        updated = {}
        for key, value in spec.items():
            if key in {"t", "h", "s", "left", "right", "tl", "tr", "bl", "br"} and isinstance(value, str):
                updated[key] = rewrite_binding(value, layer_names, shift_key_map, env_key_map, scroll_map, layer_map)
            else:
                updated[key] = value
        return updated

    return spec


def normalize_keymap(data: dict[str, Any]) -> dict[str, Any]:
    layer_names = list(data["layers"].keys())

    shift_key_map = {src: dst for src, dst, *_ in parse_array_entries(LAYOUT_SHIFT_MAP_FILE, "layout_map")}
    scroll_map = {src: dst for src, dst in parse_array_entries(LAYOUT_SHIFT_MAP_FILE, "msc_map")}
    layer_map = {int(src): int(dst) for src, dst in parse_array_entries(LAYOUT_SHIFT_MAP_FILE, "layer_map")}
    env_key_map = {src: dst for src, dst, *_ in parse_array_entries(LAYOUT_ENV_MAP_FILE, "layout_map")}

    for layer_name, keys in data["layers"].items():
        data["layers"][layer_name] = [
            rewrite_key_spec(key, layer_names, shift_key_map, env_key_map, scroll_map, layer_map) for key in keys
        ]

    for combo in data.get("combos", []):
        combo["k"] = rewrite_key_spec(combo["k"], layer_names, shift_key_map, env_key_map, scroll_map, layer_map)

    return data


def run() -> None:
    keymap_bin = Path(os.environ.get("KEYMAP_BIN", "keymap"))
    layout_name = load_layout_name()
    OUTPUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SVG.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as temp_dir:
        raw_yaml = Path(temp_dir) / f"{PROJECT_NAME}.raw.yaml"

        subprocess.run(
            [
                str(keymap_bin),
                "-c",
                str(KEYMAP_DRAWER_CONFIG),
                "parse",
                "-z",
                str(KEYMAP_FILE),
                "-o",
                str(raw_yaml),
            ],
            check=True,
            cwd=ROOT,
        )

        parsed = yaml.safe_load(raw_yaml.read_text())
        normalized = normalize_keymap(parsed)
        OUTPUT_YAML.write_text(yaml.safe_dump(normalized, allow_unicode=True, sort_keys=False, width=120))

    subprocess.run(
        [
            str(keymap_bin),
            "-c",
            str(KEYMAP_DRAWER_CONFIG),
            "draw",
            "-j",
            str(LAYOUT_INFO_FILE),
            "-l",
            layout_name,
            str(OUTPUT_YAML),
            "-o",
            str(OUTPUT_SVG),
        ],
        check=True,
        cwd=ROOT,
    )


if __name__ == "__main__":
    run()
