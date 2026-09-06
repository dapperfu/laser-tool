"""TOML configuration load, validate, and generate."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from laser.svg_layers import list_layers_from_svgs

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

CANONICAL_LAYERS = ("cut", "engrave")
DEFAULT_CONFIG_NAME = "config.toml"

CUT_DEFAULTS = {"cutting_speed": 250.0, "power": 255}
ENGRAVE_DEFAULTS = {"cutting_speed": 1000.0, "power": 75}
EXTRA_LAYER_DEFAULTS = {"cutting_speed": 750.0, "power": 128}


def sibling_toml_path(svg_path: str | Path) -> Path:
    """Return ``<svg-stem>.toml`` next to the SVG (e.g. EngraveCut.svg → EngraveCut.toml)."""
    return Path(svg_path).with_suffix(".toml")


def default_generate_config_path(svg_files: list[str] | tuple[str, ...] | None) -> Path:
    """Default write path: sibling ``.toml`` for one SVG, otherwise ``config.toml`` in cwd."""
    if svg_files and len(svg_files) == 1:
        return sibling_toml_path(svg_files[0])
    return Path.cwd() / DEFAULT_CONFIG_NAME


def find_config_file(explicit_path: str | None, svg_path: str | Path | None = None) -> Path | None:
    """Find a configuration file.

    Order: ``-c`` path, ``<svg-stem>.toml`` beside the SVG then in cwd,
    ``config.toml`` in cwd, then ``LASER_GCODE_CONFIG``.
    """
    if explicit_path:
        path = Path(explicit_path)
        return path if path.exists() else None

    candidates: list[Path] = []
    if svg_path is not None:
        svg = Path(svg_path)
        candidates.append(sibling_toml_path(svg))
        cwd_named = Path.cwd() / f"{svg.stem}.toml"
        if cwd_named.resolve() != candidates[0].resolve():
            candidates.append(cwd_named)

    candidates.append(Path.cwd() / DEFAULT_CONFIG_NAME)

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.exists():
            return path

    env_var = os.getenv("LASER_GCODE_CONFIG")
    if env_var:
        path = Path(env_var)
        return path if path.exists() else None

    return None


def load_config(config_path: str | None = None, svg_path: str | Path | None = None) -> dict:
    """Load and validate configuration from a TOML file."""
    if tomllib is None:
        raise ImportError("TOML support requires tomli for Python < 3.11. Install with: pip install tomli")

    resolved_path = find_config_file(config_path, svg_path=svg_path)
    if resolved_path is None:
        hint = ""
        if svg_path is not None:
            hint = f" Looked for {sibling_toml_path(svg_path)} then {DEFAULT_CONFIG_NAME}."
        raise FileNotFoundError(
            "Configuration file not found."
            + hint
            + " Use 'laser-gcode config generate' to create one, or specify with --config/-c"
        )

    with open(resolved_path, "rb") as f:
        config = tomllib.load(f)

    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate configuration structure and values."""
    if "global" not in config:
        raise ValueError("Configuration must have a [global] section")

    global_config = config["global"]

    validations = [
        ("unit", str, ["mm", "in"]),
        ("travel_speed", (int, float), lambda x: x > 0),
        ("passes", int, lambda x: x > 0),
        ("pass_depth", (int, float), lambda x: x > 0),
        ("dwell_time", (int, float), lambda x: x >= 0),
        ("approximation_tolerance", (int, float), lambda x: x > 0),
        ("machine_origin", str, ["bottom-left", "center", "top-left"]),
        ("zero_machine", bool, None),
        ("invert_y_axis", bool, None),
        ("use_document_size", bool, None),
        ("bed_width", (int, float), lambda x: x > 0),
        ("bed_height", (int, float), lambda x: x > 0),
        ("scaling_factor", (int, float), lambda x: x > 0),
        ("do_z_axis_start", bool, None),
        ("move_to_origin_end", bool, None),
        ("do_laser_off_start", bool, None),
        ("do_laser_off_end", bool, None),
    ]

    for key, expected_type, constraint in validations:
        if key not in global_config:
            continue
        value = global_config[key]
        if not isinstance(value, expected_type):
            raise ValueError(f"Invalid type for global.{key}: expected {expected_type}, got {type(value).__name__}")
        if constraint is None:
            continue
        if isinstance(constraint, list):
            if value not in constraint:
                raise ValueError(f"Invalid value for global.{key}: {value}. Must be one of: {constraint}")
        elif callable(constraint) and not constraint(value):
            raise ValueError(f"Invalid value for global.{key}: {value}")

    for section_name, section_data in config.items():
        if section_name == "global":
            continue
        if not isinstance(section_data, dict):
            raise ValueError(f"Section [{section_name}] must be a table")
        if "cutting_speed" in section_data:
            cutting_speed = section_data["cutting_speed"]
            if not isinstance(cutting_speed, (int, float)) or cutting_speed <= 0:
                raise ValueError(f"Invalid cutting_speed in [{section_name}]: must be positive number")
        if "power" in section_data:
            power = section_data["power"]
            if not isinstance(power, int) or not (0 <= power <= 255):
                raise ValueError(f"Invalid power in [{section_name}]: must be integer 0-255")


def toml_table_header(name: str) -> str:
    """Return a TOML table header, quoting keys that are not bare."""
    if name.replace("-", "").replace("_", "").isalnum() and name[0].isalpha():
        return f"[{name}]"
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'["{escaped}"]'


def _layer_block(name: str, cutting_speed: float, power: int, *, commented: bool) -> str:
    header = toml_table_header(name)
    assignments = [
        f"{header}",
        "# Cutting speed for this layer (unit/min)",
        f"# Default: {float(cutting_speed)}",
        "# Valid range: > 0",
        f"cutting_speed = {float(cutting_speed)}",
        "",
        "# Power for this layer (0-255)",
        f"# Default: {power}",
        "# Valid range: 0-255",
        f"power = {power}",
    ]
    if not commented:
        return "\n".join(assignments)
    commented_lines = []
    for line in assignments:
        if not line:
            commented_lines.append("#")
        elif line.startswith("#"):
            commented_lines.append(line)
        else:
            commented_lines.append(f"# {line}")
    return "\n".join(commented_lines)


def generate_config_from_svgs(svg_paths: list[str] | None = None) -> str:
    """
    Build a documented TOML config string.

    Always includes uncommented [global], [cut], and [engrave]. Extra layers
    found in the SVGs are included as commented-out tables.
    """
    extra_layers: list[str] = []
    if svg_paths:
        for label in list_layers_from_svgs(svg_paths):
            if label not in CANONICAL_LAYERS:
                extra_layers.append(label)

    extra_section = ""
    if extra_layers:
        blocks = [
            _layer_block(
                name,
                EXTRA_LAYER_DEFAULTS["cutting_speed"],
                EXTRA_LAYER_DEFAULTS["power"],
                commented=True,
            )
            for name in extra_layers
        ]
        extra_section = (
            "\n\n# Additional layers from the SVG (commented out — uncomment to enable)\n"
            "# Settings in layer sections override global settings for that layer\n\n" + "\n\n".join(blocks) + "\n"
        )

    svg_note = ""
    if svg_paths:
        names = ", ".join(Path(p).name for p in svg_paths)
        svg_note = f"# Source SVG(s): {names}\n"

    cut_block = _layer_block("cut", CUT_DEFAULTS["cutting_speed"], CUT_DEFAULTS["power"], commented=False)
    engrave_block = _layer_block(
        "engrave", ENGRAVE_DEFAULTS["cutting_speed"], ENGRAVE_DEFAULTS["power"], commented=False
    )

    return f"""# Laser G-code configuration
# Generated by: laser-gcode config generate
{svg_note}# This file contains global settings and layer-specific settings

# Global settings (apply to all layers)
[global]
# Unit of measurement
# Options:
#   - "mm": Millimeters
#   - "in": Inches
# Default: "mm"
unit = "mm"

# Travel speed for all layers (unit/min)
# Default: 3000.0
# Valid range: > 0
travel_speed = 3000.0

# Number of passes
# Default: 1
# Valid range: > 0
passes = 1

# Pass depth (unit)
# Default: 1.0
# Valid range: > 0
pass_depth = 1.0

# Dwell time before moving (ms)
# Default: 0.0
# Valid range: >= 0
dwell_time = 0.0

# Approximation tolerance
# Default: 0.01
# Valid range: > 0
approximation_tolerance = 0.01

# Tool off command (G-code)
# Default: "M5;"
tool_off_command = "M5;"

# Machine origin
# Options:
#   - "bottom-left": Origin at bottom-left corner
#   - "center": Origin at center of bed
#   - "top-left": Origin at top-left corner
# Default: "bottom-left"
machine_origin = "bottom-left"

# Zero machine coordinates (G92)
# Default: false
zero_machine = false

# Invert Y-axis
# Default: false
invert_y_axis = false

# Use document size as bed size
# Default: true
use_document_size = true

# Bed X width (unit)
# Default: 200.0
# Valid range: > 0
bed_width = 200.0

# Bed Y length (unit)
# Default: 200.0
# Valid range: > 0
bed_height = 200.0

# G-code X offset (unit)
# Default: 0.0
horizontal_offset = 0.0

# G-code Y offset (unit)
# Default: 0.0
vertical_offset = 0.0

# G-code scaling factor
# Default: 1.0
# Valid range: > 0
scaling_factor = 1.0

# Absolute Z-axis start position (unit)
# Default: 0.0
z_axis_start = 0.0

# Set Z-axis start position
# Default: false
do_z_axis_start = false

# Move to origin when done
# Default: false
move_to_origin_end = false

# Turn laser off before job
# Default: true
do_laser_off_start = true

# Turn laser off after job
# Default: true
do_laser_off_end = true

# Layer-specific settings
# Settings in layer sections override global settings for that layer
# If a layer exists in the SVG with the same name as a section, use that section's settings
# Layers other than cut and engrave are generated commented out; uncomment to enable

# Cut layer settings
{cut_block}

# Engrave layer settings
{engrave_block}
{extra_section}"""


def enabled_layer_names(config: dict) -> list[str]:
    """Return uncommented layer table names in file order (excludes [global])."""
    return [name for name in config if name != "global"]
