"""Persist only user preferences; device/firmware paths always come from HAL.

Preferences are scoped to the hardware fingerprint on the CONSOLE pendrive.
The runtime TOML remains writable by xemu, including during renderer restarts.
"""

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib


FIELDS = {
    ("sys", "mem_limit"): lambda v: type(v) is str and v in ("64", "128"),
    ("display", "renderer"): lambda v: type(v) is str and v in ("OPENGL", "VULKAN"),
    ("display.quality", "surface_scale"): lambda v: type(v) is int and 1 <= v <= 10,
    ("display.window", "vsync"): lambda v: type(v) is bool,
}


def profile(path):
    values = dict(line.split("=", 1) for line in Path(path).read_text().splitlines() if "=" in line)
    if not re.fullmatch(r"[a-f0-9]{12}", values.get("fingerprint", "")):
        raise ValueError("fingerprint ausente/invalido")
    return values


def extract(data):
    result = {}
    for (section, key), valid in FIELDS.items():
        node = data
        for part in section.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        value = node.get(key) if isinstance(node, dict) else None
        if valid(value):
            result[f"{section}.{key}"] = value
    return result


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
            name = f.name
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def restore(runtime, profile_path, console):
    hardware = profile(profile_path)
    saved = Path(console) / "config" / "xemu" / (hardware["fingerprint"] + ".json")
    if not saved.exists():
        return
    values = json.loads(saved.read_text())
    if not isinstance(values, dict):
        raise ValueError("preferencias devem ser um objeto")
    # Never force Vulkan on hardware that HAL identified as unsupported.
    if hardware.get("vulkan") != "yes" and values.get("display.renderer") == "VULKAN":
        values.pop("display.renderer")
        print("preferences: Vulkan indisponivel; usando renderer da HAL", file=sys.stderr)
    section = ""
    lines = []
    for line in Path(runtime).read_text().splitlines(keepends=True):
        match = re.fullmatch(r"\[([^]]+)\]\s*", line.strip())
        if match:
            section = match[1]
        key = line.split("=", 1)[0].strip()
        value = values.get(f"{section}.{key}")
        valid = FIELDS.get((section, key))
        if valid and valid(value):
            line = f"{key} = {json.dumps(value)}\n"
        lines.append(line)
    # Keep ownership of the runtime config (configure.sh sets it afterwards).
    Path(runtime).write_text("".join(lines))


def capture(runtime, profile_path, run):
    hardware = profile(profile_path)
    values = extract(tomllib.loads(Path(runtime).read_text()))
    atomic_write(Path(run) / "xemu-preferences.json", json.dumps({
        "fingerprint": hardware["fingerprint"], "values": values,
    }) + "\n")


def commit(run, console):
    staged = Path(run) / "xemu-preferences.json"
    if not staged.exists():
        return
    data = json.loads(staged.read_text())
    fingerprint = data["fingerprint"]
    if not re.fullmatch(r"[a-f0-9]{12}", fingerprint):
        raise ValueError("fingerprint invalido")
    target = Path(console) / "config" / "xemu" / (fingerprint + ".json")
    text = json.dumps(data["values"], sort_keys=True, indent=2) + "\n"
    if not target.exists() or target.read_text() != text:
        atomic_write(target, text)


if __name__ == "__main__":
    try:
        {"restore": restore, "capture": capture, "commit": commit}[sys.argv[1]](*sys.argv[2:])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"preferences: {exc}", file=sys.stderr)
        # Corrupt saved settings must not prevent the console from booting.
        sys.exit(0 if sys.argv[1] == "restore" else 1)
