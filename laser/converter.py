"""
Core SVG to G-code conversion logic.

This module provides reusable functions for converting SVG files to G-code,
which can be used by both the Inkscape extension and the CLI tool.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from xml.etree import ElementTree

laser_dir = Path(__file__).parent
if str(laser_dir) not in sys.path:
    sys.path.insert(0, str(laser_dir))

# Import svg_to_gcode - it's in laser/svg_to_gcode/ but when laser/ is in path,
# we can import it directly as svg_to_gcode
from svg_to_gcode import TOLERANCES
from svg_to_gcode.compiler import Compiler
from svg_to_gcode.compiler import interfaces
from svg_to_gcode.svg_parser import parse_root, parse_file
from svg_to_gcode.svg_parser import Transformation


def extract_number(input_str: str) -> Optional[float]:
    """
    Extract numeric value from a string.

    Args:
        input_str: String containing a number (may include units)

    Returns:
        Extracted float value, or None if no number found
    """
    if not input_str:
        return None

    num_str = ''
    for char in input_str:
        if char.isdigit() or char == '.':
            num_str += char
        elif num_str:
            break

    return float(num_str) if num_str else None


def generate_custom_interface(laser_off_command: str, laser_power_command: str):
    """
    Generate a custom Gcode interface with custom laser commands.

    Args:
        laser_off_command: G-code command to turn laser off
        laser_power_command: G-code command to set laser power

    Returns:
        CustomInterface class
    """
    class CustomInterface(interfaces.Gcode):
        """A Gcode interface with a custom laser power command"""

        def __init__(self):
            super().__init__()

        def laser_off(self):
            return f"{laser_off_command}"

        def set_laser_power(self, _):
            return f"{laser_power_command}"

    return CustomInterface


class ConversionConfig:
    """Configuration for SVG to G-code conversion."""

    def __init__(
        self,
        unit: str = "mm",
        travel_speed: float = 3000,
        cutting_speed: float = 750,
        passes: int = 1,
        pass_depth: float = 1,
        dwell_time: float = 0,
        approximation_tolerance: float = 0.01,
        tool_power_command: str = "M3 S255;",
        tool_off_command: str = "M5;",
        machine_origin: str = "bottom-left",
        zero_machine: bool = False,
        invert_y_axis: bool = False,
        use_document_size: bool = False,
        bed_width: float = 200,
        bed_height: float = 200,
        horizontal_offset: float = 0,
        vertical_offset: float = 0,
        scaling_factor: float = 1,
        do_z_axis_start: bool = False,
        z_axis_start: float = 0,
        move_to_origin_end: bool = False,
        do_laser_off_start: bool = True,
        do_laser_off_end: bool = True,
        layer_name: Optional[str] = None,
        header: Optional[List[str]] = None,
        footer: Optional[List[str]] = None,
    ):
        self.unit = unit
        self.travel_speed = travel_speed
        self.cutting_speed = cutting_speed
        self.passes = passes
        self.pass_depth = pass_depth
        self.dwell_time = dwell_time
        self.approximation_tolerance = approximation_tolerance
        self.tool_power_command = tool_power_command
        self.tool_off_command = tool_off_command
        self.machine_origin = machine_origin
        self.zero_machine = zero_machine
        self.invert_y_axis = invert_y_axis
        self.use_document_size = use_document_size
        self.bed_width = bed_width
        self.bed_height = bed_height
        self.horizontal_offset = horizontal_offset
        self.vertical_offset = vertical_offset
        self.scaling_factor = scaling_factor
        self.do_z_axis_start = do_z_axis_start
        self.z_axis_start = z_axis_start
        self.move_to_origin_end = move_to_origin_end
        self.do_laser_off_start = do_laser_off_start
        self.do_laser_off_end = do_laser_off_end
        self.layer_name = layer_name.strip() if layer_name else None
        self.header = header or []
        self.footer = footer or []


def get_bed_size(root: ElementTree.Element, config: ConversionConfig) -> tuple[float, float]:
    """
    Get bed size from document or configuration.

    Args:
        root: SVG root element
        config: Conversion configuration

    Returns:
        Tuple of (bed_width, bed_height)
    """
    if config.use_document_size:
        bed_width = extract_number(root.get("width", ""))
        bed_height = extract_number(root.get("height", ""))
        if bed_width is None or bed_height is None:
            raise ValueError("Document size not found in SVG")
        return bed_width, bed_height
    else:
        return config.bed_width, config.bed_height


def build_transformation(config: ConversionConfig, bed_width: float, bed_height: float) -> Transformation:
    """
    Build transformation matrix from configuration.

    Args:
        config: Conversion configuration
        bed_width: Bed width
        bed_height: Bed height

    Returns:
        Transformation object
    """
    transformation = Transformation()

    transformation.add_translation(config.horizontal_offset, config.vertical_offset)
    transformation.add_scale(config.scaling_factor)

    if config.machine_origin == "center":
        transformation.add_translation(-bed_width / 2, bed_height / 2)
    elif config.machine_origin == "top-left":
        transformation.add_translation(0, bed_height)

    return transformation


def build_header_footer(config: ConversionConfig) -> tuple[List[str], List[str]]:
    """
    Build header and footer commands from configuration.

    Args:
        config: Conversion configuration

    Returns:
        Tuple of (header, footer) command lists
    """
    custom_interface = generate_custom_interface(
        config.tool_off_command, config.tool_power_command
    )
    interface_instance = custom_interface()

    header = list(config.header)
    footer = list(config.footer)

    if config.zero_machine:
        header.append(interface_instance.set_origin_at_position())

    if config.do_laser_off_start:
        header.append(interface_instance.laser_off())
    if config.do_laser_off_end:
        footer.append(interface_instance.laser_off())

    header.append(interface_instance.set_movement_speed(config.travel_speed))
    if config.do_z_axis_start:
        header.append(interface_instance.linear_move(z=config.z_axis_start))
    if config.move_to_origin_end:
        footer.append(interface_instance.set_movement_speed(config.travel_speed))
        footer.append(interface_instance.linear_move(x=0, y=0))

    return header, footer


def convert_svg_to_gcode(
    svg_path: str,
    output_path: str,
    config: ConversionConfig,
) -> None:
    """
    Convert SVG file to G-code.

    Args:
        svg_path: Path to input SVG file
        output_path: Path to output G-code file
        config: Conversion configuration
    """
    # Set approximation tolerance
    TOLERANCES["approximation"] = config.approximation_tolerance

    # Parse SVG
    root = ElementTree.parse(svg_path).getroot()

    # Get bed size
    bed_width, bed_height = get_bed_size(root, config)

    # Build transformation
    transformation = build_transformation(config, bed_width, bed_height)

    # Parse curves
    layer_name = config.layer_name
    curves = parse_root(
        root,
        transform_origin=not config.invert_y_axis,
        root_transformation=transformation,
        canvas_height=bed_height,
        layer_name=layer_name,
    )

    # Build header and footer
    header, footer = build_header_footer(config)

    # Generate custom interface
    custom_interface = generate_custom_interface(
        config.tool_off_command, config.tool_power_command
    )

    # Create compiler
    gcode_compiler = Compiler(
        custom_interface,
        config.travel_speed,
        config.cutting_speed,
        config.pass_depth,
        dwell_time=config.dwell_time,
        custom_header=header,
        custom_footer=footer,
        unit=config.unit,
    )

    # Compile to file
    gcode_compiler.append_curves(curves)
    gcode_compiler.compile_to_file(output_path, passes=config.passes)
