"""
Combine cut and engrave layers from SVG into a single G-code file.

This module provides both a library interface and CLI tool for processing
SVG files with separate 'cut' and 'engrave' layers, generating G-code for
each layer with specific settings, and combining them into a single file.
"""

import os
import sys
import tempfile
import warnings
from pathlib import Path

# Suppress the "empty body" warning which can be a false positive
warnings.filterwarnings("ignore", message=".*Compile with an empty body.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*empty body.*")

# Add laser directory to path so svg_to_gcode can be imported
laser_dir = Path(__file__).parent
if str(laser_dir) not in sys.path:
    sys.path.insert(0, str(laser_dir))

import click  # noqa: E402

# Add Inkscape paths for inkex import (optional, only needed for SVG parsing)
try:
    from laser.inkscape_paths import add_inkscape_paths  # noqa: E402

    add_inkscape_paths()
except ImportError:
    pass

from laser.converter import ConversionConfig, convert_svg_to_gcode  # noqa: E402


class CombineConfig:
    """
    Configuration for combining cut and engrave layers.

    This class holds configuration for both engrave and cut layers,
    with separate settings for cutting speed and power for each layer.

    Parameters
    ----------
    travel_speed : float, optional
        Travel speed for both layers in unit/min (default: 3000)
    engrave_cutting_speed : float, optional
        Engrave layer cutting speed in unit/min (default: 1000)
    engrave_power : int, optional
        Engrave layer power (0-255, default: 75)
    cut_cutting_speed : float, optional
        Cut layer cutting speed in unit/min (default: 250)
    cut_power : int, optional
        Cut layer power (0-255, default: 255)
    unit : str, optional
        Unit of measurement, 'mm' or 'in' (default: 'mm')
    passes : int, optional
        Number of passes (default: 1)
    pass_depth : float, optional
        Pass depth in unit (default: 1)
    dwell_time : float, optional
        Dwell time before moving in ms (default: 0)
    approximation_tolerance : float, optional
        Approximation tolerance (default: 0.01)
    tool_off_command : str, optional
        Tool off command (default: 'M5;')
    machine_origin : str, optional
        Machine origin: 'bottom-left', 'center', or 'top-left'
        (default: 'bottom-left')
    zero_machine : bool, optional
        Zero machine coordinates (G92, default: False)
    invert_y_axis : bool, optional
        Invert Y-axis (default: False)
    use_document_size : bool, optional
        Use document size as bed size (default: True)
    bed_width : float, optional
        Bed X width in unit (default: 200)
    bed_height : float, optional
        Bed Y length in unit (default: 200)
    horizontal_offset : float, optional
        G-code X offset in unit (default: 0)
    vertical_offset : float, optional
        G-code Y offset in unit (default: 0)
    scaling_factor : float, optional
        G-code scaling factor (default: 1)
    z_axis_start : float, optional
        Absolute Z-axis start position in unit (default: 0)
    do_z_axis_start : bool, optional
        Set Z-axis start position (default: False)
    move_to_origin_end : bool, optional
        Move to origin when done (default: False)
    do_laser_off_start : bool, optional
        Turn laser off before job (default: True)
    do_laser_off_end : bool, optional
        Turn laser off after job (default: True)
    header : list of str, optional
        Custom G-code header lines (default: None)
    footer : list of str, optional
        Custom G-code footer lines (default: None)
    """

    def __init__(
        self,
        travel_speed: float = 3000,
        engrave_cutting_speed: float = 1000,
        engrave_power: int = 75,
        cut_cutting_speed: float = 250,
        cut_power: int = 255,
        unit: str = "mm",
        passes: int = 1,
        pass_depth: float = 1,
        dwell_time: float = 0,
        approximation_tolerance: float = 0.01,
        tool_off_command: str = "M5;",
        machine_origin: str = "bottom-left",
        zero_machine: bool = False,
        invert_y_axis: bool = False,
        use_document_size: bool = True,
        bed_width: float = 200,
        bed_height: float = 200,
        horizontal_offset: float = 0,
        vertical_offset: float = 0,
        scaling_factor: float = 1,
        z_axis_start: float = 0,
        do_z_axis_start: bool = False,
        move_to_origin_end: bool = False,
        do_laser_off_start: bool = True,
        do_laser_off_end: bool = True,
        header: list[str] | None = None,
        footer: list[str] | None = None,
    ):
        self.travel_speed = travel_speed
        self.engrave_cutting_speed = engrave_cutting_speed
        self.engrave_power = engrave_power
        self.cut_cutting_speed = cut_cutting_speed
        self.cut_power = cut_power
        self.unit = unit
        self.passes = passes
        self.pass_depth = pass_depth
        self.dwell_time = dwell_time
        self.approximation_tolerance = approximation_tolerance
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
        self.z_axis_start = z_axis_start
        self.do_z_axis_start = do_z_axis_start
        self.move_to_origin_end = move_to_origin_end
        self.do_laser_off_start = do_laser_off_start
        self.do_laser_off_end = do_laser_off_end
        self.header = header or []
        self.footer = footer or []

    def to_conversion_config(
        self, layer_name: str, cutting_speed: float, power: int
    ) -> ConversionConfig:
        """
        Convert to ConversionConfig for a specific layer.

        Parameters
        ----------
        layer_name : str
            Name of the layer ('engrave' or 'cut')
        cutting_speed : float
            Cutting speed for this layer
        power : int
            Power setting for this layer (0-255)

        Returns
        -------
        ConversionConfig
            Configuration object for single layer conversion
        """
        return ConversionConfig(
            unit=self.unit,
            travel_speed=self.travel_speed,
            cutting_speed=cutting_speed,
            passes=self.passes,
            pass_depth=self.pass_depth,
            dwell_time=self.dwell_time,
            approximation_tolerance=self.approximation_tolerance,
            tool_power_command=f"M3 S{power};",
            tool_off_command=self.tool_off_command,
            machine_origin=self.machine_origin,
            zero_machine=self.zero_machine,
            invert_y_axis=self.invert_y_axis,
            use_document_size=self.use_document_size,
            bed_width=self.bed_width,
            bed_height=self.bed_height,
            horizontal_offset=self.horizontal_offset,
            vertical_offset=self.vertical_offset,
            scaling_factor=self.scaling_factor,
            do_z_axis_start=self.do_z_axis_start,
            z_axis_start=self.z_axis_start,
            move_to_origin_end=self.move_to_origin_end,
            do_laser_off_start=self.do_laser_off_start,
            do_laser_off_end=self.do_laser_off_end,
            layer_name=layer_name,
            header=self.header,
            footer=self.footer,
        )


def is_empty_gcode(gcode_path: str) -> bool:
    """
    Check if G-code file is essentially empty (only header/footer, no actual cutting).

    Parameters
    ----------
    gcode_path : str
        Path to G-code file

    Returns
    -------
    bool
        True if file has no cutting commands, False otherwise
    """
    try:
        with open(gcode_path) as f:
            lines = f.readlines()

        # Count lines that are actual cutting commands (G1, G2, G3, M3 with movement)
        # Exclude header (G90, M5, G21) and footer (M5, G0 X0 Y0)
        cutting_lines = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("G1", "G2", "G3", "M3 S")):
                # Exclude feed rate only lines (G1 F...)
                if not stripped.startswith("G1 F"):
                    cutting_lines += 1

        return cutting_lines == 0
    except OSError:
        return True


def remove_gcode_footer(gcode_path: str) -> list[str]:
    """
    Remove footer from G-code file (last M5 and move commands).

    Parameters
    ----------
    gcode_path : str
        Path to G-code file

    Returns
    -------
    list of str
        G-code lines without footer
    """
    with open(gcode_path) as f:
        lines = f.readlines()

    result = []
    in_footer = False

    for line in lines:
        stripped = line.strip()
        if stripped == "M5" or stripped == "M5;":
            in_footer = True
            continue
        if in_footer and (
            stripped.startswith("G0 X0 Y0") or stripped.startswith("G0 X0 Y0 Z0")
        ):
            continue
        if in_footer and stripped == "":
            continue
        if in_footer:
            in_footer = False
        result.append(line.rstrip("\n"))

    return result


def get_gcode_body_and_footer(gcode_path: str) -> list[str]:
    """
    Extract body and footer from G-code (skip header).

    Parameters
    ----------
    gcode_path : str
        Path to G-code file

    Returns
    -------
    list of str
        G-code lines (body + footer, no header)
    """
    with open(gcode_path) as f:
        lines = f.readlines()

    result = []
    found_unit = False

    for line in lines:
        stripped = line.strip()
        if (
            stripped == "G21"
            or stripped == "G21;"
            or stripped == "G20"
            or stripped == "G20;"
        ):
            found_unit = True
            continue
        if found_unit:
            result.append(line.rstrip("\n"))

    return result


def combine_gcode_files(
    engrave_path: str | None,
    cut_path: str,
    output_path: str,
) -> None:
    """
    Combine engrave and cut G-code files into a single output file.

    The engrave file (if present) is included without footer.
    The cut file is included with body and footer only (header skipped).

    Parameters
    ----------
    engrave_path : str or None
        Path to engrave G-code file (None if engrave layer not present)
    cut_path : str
        Path to cut G-code file (required)
    output_path : str
        Path to output combined G-code file
    """
    separator = "; =========================================="
    layer_sep = "; Layer transition: Engrave -> Cut"
    separator_end = "; =========================================="

    with open(output_path, "w") as outfile:
        # Write engrave file without footer (if present)
        if engrave_path and os.path.exists(engrave_path):
            engrave_lines = remove_gcode_footer(engrave_path)
            for line in engrave_lines:
                outfile.write(line + "\n")
            outfile.write("\n")
            outfile.write(separator + "\n")
            outfile.write(layer_sep + "\n")
            outfile.write(separator_end + "\n")
            outfile.write("\n")

        # Write cut file body and footer (skip header to avoid duplicates)
        cut_lines = get_gcode_body_and_footer(cut_path)
        for line in cut_lines:
            outfile.write(line + "\n")


def generate_layer_gcode(
    svg_path: str,
    layer_name: str,
    config: CombineConfig,
    cutting_speed: float,
    power: int,
    output_path: str,
) -> bool:
    """
    Generate G-code for a single layer.

    Parameters
    ----------
    svg_path : str
        Path to input SVG file
    layer_name : str
        Name of the layer to process
    config : CombineConfig
        Combine configuration
    cutting_speed : float
        Cutting speed for this layer
    power : int
        Power setting for this layer (0-255)
    output_path : str
        Path to output G-code file

    Returns
    -------
    bool
        True if G-code was generated successfully, False otherwise
    """
    try:
        conversion_config = config.to_conversion_config(
            layer_name, cutting_speed, power
        )
        convert_svg_to_gcode(svg_path, output_path, conversion_config)
        return True
    except Exception:
        return False


def combine_cut_engrave(
    svg_path: str,
    output_path: str,
    config: CombineConfig,
    verbose: bool = True,
) -> tuple[bool, str | None]:
    """
    Combine cut and engrave layers from SVG into a single G-code file.

    Processes engrave layer first (if present), then cut layer, and combines
    them into a single output file.

    Parameters
    ----------
    svg_path : str
        Path to input SVG file
    output_path : str
        Path to output combined G-code file
    config : CombineConfig
        Configuration for combine operation
    verbose : bool, optional
        Print progress messages (default: True)

    Returns
    -------
    tuple of (bool, str or None)
        (success, error_message)
        success: True if operation succeeded, False otherwise
        error_message: Error message if failed, None if succeeded
    """
    # Create temporary files in the same directory as output
    output_dir = os.path.dirname(output_path) or "."

    # Generate engrave layer G-code
    if verbose:
        click.echo("[1/3] Generating engrave layer G-code...")
        click.echo(
            f"  Settings: Travel speed={config.travel_speed} {config.unit}/min, "
            f"Cutting speed={config.engrave_cutting_speed} {config.unit}/min, "
            f"Power=S{config.engrave_power} ({config.engrave_power * 100 // 255}%)"
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".gcode", dir=output_dir, delete=False
    ) as tmp_engrave:
        temp_engrave_path = tmp_engrave.name

    try:
        success = generate_layer_gcode(
            svg_path,
            "engrave",
            config,
            config.engrave_cutting_speed,
            config.engrave_power,
            temp_engrave_path,
        )

        if not success:
            if verbose:
                click.echo("  ✗ Failed to generate engrave layer G-code")
                click.echo(
                    "  Warning: Engrave layer may not exist in SVG, continuing with cut only..."
                )
            temp_engrave_path = None
        elif os.path.exists(temp_engrave_path) and is_empty_gcode(temp_engrave_path):
            if verbose:
                click.echo(
                    "  ⚠ Warning: Engrave layer found but contains no paths to process"
                )
                click.echo(
                    "  Hint: Make sure objects in the 'engrave' layer are converted to paths"
                )
                click.echo(
                    "        (In Inkscape: Select objects → Path → Object to Path)"
                )
                click.echo("  Continuing with cut only...")
            os.unlink(temp_engrave_path)
            temp_engrave_path = None
        elif verbose:
            click.echo("  ✓ Engrave layer G-code generated")

        if verbose:
            click.echo("")
    except Exception as e:
        if verbose:
            click.echo(f"  ✗ Error generating engrave layer: {e}")
        temp_engrave_path = None

    # Generate cut layer G-code
    if verbose:
        click.echo("[2/3] Generating cut layer G-code...")
        click.echo(
            f"  Settings: Travel speed={config.travel_speed} {config.unit}/min, "
            f"Cutting speed={config.cut_cutting_speed} {config.unit}/min, "
            f"Power=S{config.cut_power} ({config.cut_power * 100 // 255}%)"
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".gcode", dir=output_dir, delete=False
    ) as tmp_cut:
        temp_cut_path = tmp_cut.name

    try:
        success = generate_layer_gcode(
            svg_path,
            "cut",
            config,
            config.cut_cutting_speed,
            config.cut_power,
            temp_cut_path,
        )

        if not success:
            if temp_engrave_path and os.path.exists(temp_engrave_path):
                os.unlink(temp_engrave_path)
            return (
                False,
                "Failed to generate cut layer G-code. Error: Cut layer is required but not found in SVG",
            )
        elif os.path.exists(temp_cut_path) and is_empty_gcode(temp_cut_path):
            if temp_engrave_path and os.path.exists(temp_engrave_path):
                os.unlink(temp_engrave_path)
            if os.path.exists(temp_cut_path):
                os.unlink(temp_cut_path)
            error_msg = (
                "Error: Cut layer found but contains no paths to process\n\n"
                "Troubleshooting:\n"
                "1. Make sure the 'cut' layer exists in your SVG file\n"
                "2. Convert all objects in the 'cut' layer to paths:\n"
                "   - In Inkscape: Select objects → Path → Object to Path\n"
                "3. Verify layer names match exactly (case-sensitive): 'cut' and 'engrave'\n"
                "4. Check that the layers contain actual path elements, not just shapes"
            )
            return False, error_msg
        elif verbose:
            click.echo("  ✓ Cut layer G-code generated")

        if verbose:
            click.echo("")
    except Exception as e:
        if temp_engrave_path and os.path.exists(temp_engrave_path):
            os.unlink(temp_engrave_path)
        if os.path.exists(temp_cut_path):
            os.unlink(temp_cut_path)
        return False, f"Error generating cut layer: {e}"

    # Combine G-code files
    if verbose:
        click.echo("[3/3] Combining G-code files...")
        click.echo("  Order: Engrave first, then Cut")

    try:
        # Read line counts before combining (needed for summary)
        engrave_lines = 0
        if temp_engrave_path and os.path.exists(temp_engrave_path):
            with open(temp_engrave_path) as f:
                engrave_lines = len(f.readlines())
        
        cut_lines = 0
        if os.path.exists(temp_cut_path):
            with open(temp_cut_path) as f:
                cut_lines = len(f.readlines())
        
        combine_gcode_files(temp_engrave_path, temp_cut_path, output_path)

        # Cleanup temporary files
        if temp_engrave_path and os.path.exists(temp_engrave_path):
            os.unlink(temp_engrave_path)
        if os.path.exists(temp_cut_path):
            os.unlink(temp_cut_path)

        if verbose:
            click.echo("  ✓ Successfully created combined G-code file")
            click.echo("")
            click.echo("==========================================")
            click.echo("Summary")
            click.echo("==========================================")
            click.echo(f"Output file: {output_path}")
            if temp_engrave_path and engrave_lines > 0:
                click.echo(
                    f"Engrave layer: {engrave_lines} lines "
                    f"(speed: {config.engrave_cutting_speed} {config.unit}/min, "
                    f"power: S{config.engrave_power})"
                )
            if cut_lines > 0:
                click.echo(
                    f"Cut layer:    {cut_lines} lines "
                    f"(speed: {config.cut_cutting_speed} {config.unit}/min, "
                    f"power: S{config.cut_power})"
                )
            with open(output_path) as f:
                total_lines = len(f.readlines())
            click.echo(f"Total:        {total_lines} lines")
            click.echo("")
            click.echo("The G-code file is ready for use with your laser cutter!")

        return True, None
    except Exception as e:
        # Cleanup temporary files
        if temp_engrave_path and os.path.exists(temp_engrave_path):
            os.unlink(temp_engrave_path)
        if os.path.exists(temp_cut_path):
            os.unlink(temp_cut_path)
        return False, f"Failed to create combined G-code file: {e}"


@click.command()
@click.argument("svg_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output G-code file path (default: input filename with .gcode extension)",
)
@click.option(
    "--travel-speed",
    type=float,
    default=3000,
    help="Travel speed for both layers (unit/min, default: 3000)",
)
@click.option(
    "--engrave-cutting-speed",
    type=float,
    default=1000,
    help="Engrave layer cutting speed (unit/min, default: 1000)",
)
@click.option(
    "--engrave-power",
    type=int,
    default=75,
    help="Engrave layer power (0-255, default: 75)",
)
@click.option(
    "--cut-cutting-speed",
    type=float,
    default=250,
    help="Cut layer cutting speed (unit/min, default: 250)",
)
@click.option(
    "--cut-power", type=int, default=255, help="Cut layer power (0-255, default: 255)"
)
@click.option(
    "--unit",
    "-u",
    type=click.Choice(["mm", "in"], case_sensitive=False),
    default="mm",
    help="Unit of measurement (default: mm)",
)
@click.option(
    "--passes", "-p", type=int, default=1, help="Number of passes (default: 1)"
)
@click.option(
    "--pass-depth", type=float, default=1, help="Pass depth (unit, default: 1)"
)
@click.option(
    "--dwell-time",
    type=float,
    default=0,
    help="Dwell time before moving (ms, default: 0)",
)
@click.option(
    "--approximation-tolerance",
    type=float,
    default=0.01,
    help="Approximation tolerance (default: 0.01)",
)
@click.option(
    "--tool-off-command",
    type=str,
    default="M5;",
    help="Tool off command (default: M5;)",
)
@click.option(
    "--machine-origin",
    type=click.Choice(["bottom-left", "center", "top-left"], case_sensitive=False),
    default="bottom-left",
    help="Machine origin (default: bottom-left)",
)
@click.option(
    "--zero-machine/--no-zero-machine",
    default=False,
    help="Zero machine coordinates (G92, default: False)",
)
@click.option(
    "--invert-y-axis/--no-invert-y-axis",
    default=False,
    help="Invert Y-axis (default: False)",
)
@click.option(
    "--use-document-size/--no-use-document-size",
    default=True,
    help="Use document size as bed size (default: True)",
)
@click.option(
    "--bed-width", type=float, default=200, help="Bed X width (unit, default: 200)"
)
@click.option(
    "--bed-height", type=float, default=200, help="Bed Y length (unit, default: 200)"
)
@click.option(
    "--horizontal-offset",
    type=float,
    default=0,
    help="G-code X offset (unit, default: 0)",
)
@click.option(
    "--vertical-offset",
    type=float,
    default=0,
    help="G-code Y offset (unit, default: 0)",
)
@click.option(
    "--scaling-factor", type=float, default=1, help="G-code scaling factor (default: 1)"
)
@click.option(
    "--z-axis-start",
    type=float,
    default=0,
    help="Absolute Z-axis start position (unit, default: 0)",
)
@click.option(
    "--do-z-axis-start/--no-do-z-axis-start",
    default=False,
    help="Set Z-axis start position (default: False)",
)
@click.option(
    "--move-to-origin-end/--no-move-to-origin-end",
    default=False,
    help="Move to origin when done (default: False)",
)
@click.option(
    "--do-laser-off-start/--no-do-laser-off-start",
    default=True,
    help="Turn laser off before job (default: True)",
)
@click.option(
    "--do-laser-off-end/--no-do-laser-off-end",
    default=True,
    help="Turn laser off after job (default: True)",
)
@click.option(
    "--header-file",
    type=click.Path(exists=True, readable=True),
    help="Custom G-code header file",
)
@click.option(
    "--footer-file",
    type=click.Path(exists=True, readable=True),
    help="Custom G-code footer file",
)
def main(
    svg_file: str,
    output: str | None,
    travel_speed: float,
    engrave_cutting_speed: float,
    engrave_power: int,
    cut_cutting_speed: float,
    cut_power: int,
    unit: str,
    passes: int,
    pass_depth: float,
    dwell_time: float,
    approximation_tolerance: float,
    tool_off_command: str,
    machine_origin: str,
    zero_machine: bool,
    invert_y_axis: bool,
    use_document_size: bool,
    bed_width: float,
    bed_height: float,
    horizontal_offset: float,
    vertical_offset: float,
    scaling_factor: float,
    z_axis_start: float,
    do_z_axis_start: bool,
    move_to_origin_end: bool,
    do_laser_off_start: bool,
    do_laser_off_end: bool,
    header_file: str | None,
    footer_file: str | None,
):
    """
    Combine cut and engrave layers from SVG into a single G-code file.

    Processes an SVG file with 'cut' and 'engrave' layers, generates G-code
    for each layer with specific settings, and combines them into a single
    file with engrave first, then cut.

    SVG_FILE: Path to input SVG file
    """
    click.echo("==========================================")
    click.echo("Combining Cut and Engrave Layers")
    click.echo("==========================================")
    click.echo(f"Input SVG:  {svg_file}")

    # Determine output path
    if output:
        output_path = output
    else:
        svg_path = Path(svg_file)
        output_path = str(svg_path.with_suffix(".gcode"))

    click.echo(f"Output:     {output_path}")
    click.echo("")

    # Load header and footer files
    header = []
    if header_file:
        with open(header_file) as f:
            header = f.read().splitlines()

    footer = []
    if footer_file:
        with open(footer_file) as f:
            footer = f.read().splitlines()

    # Create configuration
    config = CombineConfig(
        travel_speed=travel_speed,
        engrave_cutting_speed=engrave_cutting_speed,
        engrave_power=engrave_power,
        cut_cutting_speed=cut_cutting_speed,
        cut_power=cut_power,
        unit=unit,
        passes=passes,
        pass_depth=pass_depth,
        dwell_time=dwell_time,
        approximation_tolerance=approximation_tolerance,
        tool_off_command=tool_off_command,
        machine_origin=machine_origin,
        zero_machine=zero_machine,
        invert_y_axis=invert_y_axis,
        use_document_size=use_document_size,
        bed_width=bed_width,
        bed_height=bed_height,
        horizontal_offset=horizontal_offset,
        vertical_offset=vertical_offset,
        scaling_factor=scaling_factor,
        z_axis_start=z_axis_start,
        do_z_axis_start=do_z_axis_start,
        move_to_origin_end=move_to_origin_end,
        do_laser_off_start=do_laser_off_start,
        do_laser_off_end=do_laser_off_end,
        header=header,
        footer=footer,
    )

    # Combine layers
    success, error_message = combine_cut_engrave(svg_file, output_path, config)

    if not success:
        click.echo(f"Error: {error_message}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
