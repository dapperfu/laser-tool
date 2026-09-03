"""
Backward-compatible exports for cut/engrave conversion.

Prefer ``laser.convert_job`` and ``laser-gcode`` (``laser.cli``).
"""

from laser.cli import cli, entry_point
from laser.config import (
    find_config_file,
    generate_config_from_svgs,
    load_config,
    validate_config,
)
from laser.convert_job import (
    combine_layer_gcode_files,
    convert_svg_layers,
    generate_layer_gcode,
    get_gcode_body_and_footer,
    is_empty_gcode,
    remove_gcode_footer,
)

# Historical name used by the old CLI
combine_gcode_files = combine_layer_gcode_files
combine_cut_engrave = convert_svg_layers
generate_config_template = generate_config_from_svgs

__all__ = [
    "cli",
    "entry_point",
    "combine_layer_gcode_files",
    "combine_gcode_files",
    "combine_cut_engrave",
    "convert_svg_layers",
    "generate_layer_gcode",
    "get_gcode_body_and_footer",
    "is_empty_gcode",
    "remove_gcode_footer",
    "find_config_file",
    "generate_config_from_svgs",
    "generate_config_template",
    "load_config",
    "validate_config",
]


if __name__ == "__main__":
    entry_point()
