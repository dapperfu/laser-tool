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

# TOML library support (per .cursor/rules/python/toml-config.mdc)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

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

    def to_conversion_config(self, layer_name: str, cutting_speed: float, power: int) -> ConversionConfig:
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
        if in_footer and (stripped.startswith("G0 X0 Y0") or stripped.startswith("G0 X0 Y0 Z0")):
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
        if stripped == "G21" or stripped == "G21;" or stripped == "G20" or stripped == "G20;":
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
        conversion_config = config.to_conversion_config(layer_name, cutting_speed, power)
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", dir=output_dir, delete=False) as tmp_engrave:
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
                click.echo("  Warning: Engrave layer may not exist in SVG, continuing with cut only...")
            temp_engrave_path = None
        elif os.path.exists(temp_engrave_path) and is_empty_gcode(temp_engrave_path):
            if verbose:
                click.echo("  ⚠ Warning: Engrave layer found but contains no paths to process")
                click.echo("  Hint: Make sure objects in the 'engrave' layer are converted to paths")
                click.echo("        (In Inkscape: Select objects → Path → Object to Path)")
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", dir=output_dir, delete=False) as tmp_cut:
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


# ============================================================================
# Configuration File Support
# ============================================================================


def find_config_file(explicit_path: str | None) -> Path | None:
    """
    Find configuration file following lookup order.

    Parameters
    ----------
    explicit_path : str or None
        Explicit path provided via --config option

    Returns
    -------
    Path or None
        Path to config file if found, None otherwise
    """
    # 1. Explicit path provided
    if explicit_path:
        path = Path(explicit_path)
        return path if path.exists() else None

    # 2. config.toml in current working directory
    cwd_config = Path.cwd() / "config.toml"
    if cwd_config.exists():
        return cwd_config

    # 3. Environment variable
    env_var = os.getenv("COMBINE_CUT_ENGRAVE_CONFIG")
    if env_var:
        path = Path(env_var)
        return path if path.exists() else None

    return None


def load_config(config_path: str | None = None) -> dict:
    """
    Load configuration from TOML file.

    Parameters
    ----------
    config_path : str or None
        Explicit path to config file, or None to use lookup order

    Returns
    -------
    dict
        Configuration dictionary

    Raises
    ------
    FileNotFoundError
        If config file not found
    ValueError
        If config file is invalid
    """
    if tomllib is None:
        raise ImportError("TOML support requires tomli for Python < 3.11. Install with: pip install tomli")

    resolved_path = find_config_file(config_path)

    if resolved_path is None:
        raise FileNotFoundError(
            "Configuration file not found. "
            "Use 'combine-cut-engrave config generate' to create one, "
            "or specify with --config/-c"
        )

    with open(resolved_path, "rb") as f:
        config = tomllib.load(f)

    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """
    Validate configuration structure and values.

    Parameters
    ----------
    config : dict
        Configuration dictionary to validate

    Raises
    ------
    ValueError
        If configuration is invalid
    """
    # Check for global section
    if "global" not in config:
        raise ValueError("Configuration must have a [global] section")

    global_config = config["global"]

    # Validate global settings types and ranges
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
        if key in global_config:
            value = global_config[key]
            # Type check
            if not isinstance(value, expected_type):
                raise ValueError(f"Invalid type for global.{key}: expected {expected_type}, got {type(value).__name__}")
            # Constraint check
            if constraint is not None:
                if isinstance(constraint, list):
                    if value not in constraint:
                        raise ValueError(f"Invalid value for global.{key}: {value}. Must be one of: {constraint}")
                elif callable(constraint):
                    if not constraint(value):
                        raise ValueError(f"Invalid value for global.{key}: {value}")

    # Validate layer sections
    for section_name, section_data in config.items():
        if section_name == "global":
            continue

        if not isinstance(section_data, dict):
            raise ValueError(f"Section [{section_name}] must be a table")

        # Layer sections should have cutting_speed and power
        if "cutting_speed" in section_data:
            cutting_speed = section_data["cutting_speed"]
            if not isinstance(cutting_speed, (int, float)) or cutting_speed <= 0:
                raise ValueError(f"Invalid cutting_speed in [{section_name}]: must be positive number")

        if "power" in section_data:
            power = section_data["power"]
            if not isinstance(power, int) or not (0 <= power <= 255):
                raise ValueError(f"Invalid power in [{section_name}]: must be integer 0-255")


def merge_config_with_cli(config: dict, cli_args: dict) -> CombineConfig:
    """
    Merge configuration file with CLI arguments (CLI overrides config).

    Parameters
    ----------
    config : dict
        Configuration dictionary from TOML file
    cli_args : dict
        CLI arguments (from Click context)

    Returns
    -------
    CombineConfig
        Merged configuration object
    """
    global_config = config.get("global", {})
    cut_config = config.get("cut", {})
    engrave_config = config.get("engrave", {})

    # Start with CombineConfig defaults
    defaults = CombineConfig()

    # Start with global settings (override defaults)
    settings = {
        "travel_speed": global_config.get("travel_speed", defaults.travel_speed),
        "unit": global_config.get("unit", defaults.unit),
        "passes": global_config.get("passes", defaults.passes),
        "pass_depth": global_config.get("pass_depth", defaults.pass_depth),
        "dwell_time": global_config.get("dwell_time", defaults.dwell_time),
        "approximation_tolerance": global_config.get("approximation_tolerance", defaults.approximation_tolerance),
        "tool_off_command": global_config.get("tool_off_command", defaults.tool_off_command),
        "machine_origin": global_config.get("machine_origin", defaults.machine_origin),
        "zero_machine": global_config.get("zero_machine", defaults.zero_machine),
        "invert_y_axis": global_config.get("invert_y_axis", defaults.invert_y_axis),
        "use_document_size": global_config.get("use_document_size", defaults.use_document_size),
        "bed_width": global_config.get("bed_width", defaults.bed_width),
        "bed_height": global_config.get("bed_height", defaults.bed_height),
        "horizontal_offset": global_config.get("horizontal_offset", defaults.horizontal_offset),
        "vertical_offset": global_config.get("vertical_offset", defaults.vertical_offset),
        "scaling_factor": global_config.get("scaling_factor", defaults.scaling_factor),
        "z_axis_start": global_config.get("z_axis_start", defaults.z_axis_start),
        "do_z_axis_start": global_config.get("do_z_axis_start", defaults.do_z_axis_start),
        "move_to_origin_end": global_config.get("move_to_origin_end", defaults.move_to_origin_end),
        "do_laser_off_start": global_config.get("do_laser_off_start", defaults.do_laser_off_start),
        "do_laser_off_end": global_config.get("do_laser_off_end", defaults.do_laser_off_end),
    }

    # Add layer-specific settings (override global)
    settings["engrave_cutting_speed"] = engrave_config.get("cutting_speed", defaults.engrave_cutting_speed)
    settings["engrave_power"] = engrave_config.get("power", defaults.engrave_power)
    settings["cut_cutting_speed"] = cut_config.get("cutting_speed", defaults.cut_cutting_speed)
    settings["cut_power"] = cut_config.get("power", defaults.cut_power)

    # Apply CLI overrides (CLI always wins)
    cli_mapping = {
        "travel_speed": "travel_speed",
        "engrave_cutting_speed": "engrave_cutting_speed",
        "engrave_power": "engrave_power",
        "cut_cutting_speed": "cut_cutting_speed",
        "cut_power": "cut_power",
        "unit": "unit",
        "passes": "passes",
        "pass_depth": "pass_depth",
        "dwell_time": "dwell_time",
        "approximation_tolerance": "approximation_tolerance",
        "tool_off_command": "tool_off_command",
        "machine_origin": "machine_origin",
        "zero_machine": "zero_machine",
        "invert_y_axis": "invert_y_axis",
        "use_document_size": "use_document_size",
        "bed_width": "bed_width",
        "bed_height": "bed_height",
        "horizontal_offset": "horizontal_offset",
        "vertical_offset": "vertical_offset",
        "scaling_factor": "scaling_factor",
        "z_axis_start": "z_axis_start",
        "do_z_axis_start": "do_z_axis_start",
        "move_to_origin_end": "move_to_origin_end",
        "do_laser_off_start": "do_laser_off_start",
        "do_laser_off_end": "do_laser_off_end",
    }

    for cli_key, config_key in cli_mapping.items():
        if cli_key in cli_args and cli_args[cli_key] is not None:
            settings[config_key] = cli_args[cli_key]

    # Handle header and footer from config
    header = global_config.get("header", [])
    footer = global_config.get("footer", [])

    return CombineConfig(
        header=header if isinstance(header, list) else [],
        footer=footer if isinstance(footer, list) else [],
        **settings,
    )


def config_to_combine_config(config: dict, layer_name: str, cli_overrides: dict | None = None) -> CombineConfig:
    """
    Convert config dict to CombineConfig for a specific layer.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    layer_name : str
        Name of the layer (e.g., "cut", "engrave")
    cli_overrides : dict or None
        CLI argument overrides

    Returns
    -------
    CombineConfig
        Configuration object for the layer
    """
    global_config = config.get("global", {})
    layer_config = config.get(layer_name, {})

    # Start with global settings
    settings = dict(global_config)

    # Override with layer-specific settings
    if "cutting_speed" in layer_config:
        settings[f"{layer_name}_cutting_speed"] = layer_config["cutting_speed"]
    if "power" in layer_config:
        settings[f"{layer_name}_power"] = layer_config["power"]

    # Apply CLI overrides
    if cli_overrides:
        settings.update(cli_overrides)

    # Extract layer-specific settings
    engrave_cutting_speed = settings.pop("engrave_cutting_speed", 1000)
    engrave_power = settings.pop("engrave_power", 75)
    cut_cutting_speed = settings.pop("cut_cutting_speed", 250)
    cut_power = settings.pop("cut_power", 255)

    # Get cutting speed and power for this layer
    cutting_speed_key = f"{layer_name}_cutting_speed"
    power_key = f"{layer_name}_power"

    if cutting_speed_key in settings:
        layer_cutting_speed = settings.pop(cutting_speed_key)
        if layer_name == "engrave":
            engrave_cutting_speed = layer_cutting_speed
        elif layer_name == "cut":
            cut_cutting_speed = layer_cutting_speed

    if power_key in settings:
        layer_power = settings.pop(power_key)
        if layer_name == "engrave":
            engrave_power = layer_power
        elif layer_name == "cut":
            cut_power = layer_power

    # Handle header and footer
    header = settings.pop("header", [])
    footer = settings.pop("footer", [])

    return CombineConfig(
        engrave_cutting_speed=engrave_cutting_speed,
        engrave_power=engrave_power,
        cut_cutting_speed=cut_cutting_speed,
        cut_power=cut_power,
        header=header if isinstance(header, list) else [],
        footer=footer if isinstance(footer, list) else [],
        **settings,
    )


def generate_config_template() -> str:
    """
    Generate TOML config template with defaults and documentation.

    Returns
    -------
    str
        TOML configuration template
    """
    return """# Combine Cut Engrave Configuration
# Generated by: combine-cut-engrave config generate
# This file contains global settings and layer-specific settings

# Global settings (apply to all layers)
[global]
# Unit of measurement
# Options:
#   - "mm": Millimeters
#   - "in": Inches
# Default: "mm"
unit = "mm"

# Travel speed for both layers (unit/min)
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

# Cut layer settings
[cut]
# Cutting speed for cut layer (unit/min)
# Default: 250.0
# Valid range: > 0
cutting_speed = 250.0

# Power for cut layer (0-255)
# Default: 255
# Valid range: 0-255
power = 255

# Engrave layer settings
[engrave]
# Cutting speed for engrave layer (unit/min)
# Default: 1000.0
# Valid range: > 0
cutting_speed = 1000.0

# Power for engrave layer (0-255)
# Default: 75
# Valid range: 0-255
power = 75

# Additional layers can be added dynamically
# Example:
# [layer_name]
# cutting_speed = <value>
# power = <value>
"""


@click.group()
def cli():
    """Combine cut and engrave layers from SVG into G-code."""
    pass


@cli.group("config")
def config_group():
    """Configuration management commands."""
    pass


@config_group.command("generate")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Path to configuration file (default: config.toml in current directory)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing configuration file without prompting",
)
def config_generate(config: str | None, force: bool) -> None:
    """Generate default configuration file with placeholders for required values."""
    if config is None:
        config_path = Path.cwd() / "config.toml"
    else:
        config_path = Path(config)

    if config_path.exists() and not force:
        if not click.confirm(f"Configuration file exists at {config_path}. Overwrite?"):
            click.echo("Aborted.")
            return

    # Generate config with defaults and documentation
    config_content = generate_config_template()
    config_path.write_text(config_content, encoding="utf-8")

    click.echo(f"Configuration file generated at {config_path}")
    click.echo("You can now edit the configuration file to customize settings.")


@config_group.command("validate")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Path to configuration file to validate",
)
def config_validate(config: str | None) -> None:
    """Validate configuration file."""
    if tomllib is None:
        click.echo(
            "Error: TOML support requires tomli for Python < 3.11. Install with: pip install tomli",
            err=True,
        )
        sys.exit(1)

    config_path = find_config_file(config)

    if config_path is None:
        click.echo("Error: Configuration file not found.", err=True)
        sys.exit(1)

    try:
        config_data = load_config(str(config_path))
        validate_config(config_data)
        click.echo(f"Configuration file {config_path} is valid.")
    except Exception as e:
        click.echo(f"Error: Configuration file is invalid: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("svg_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, readable=True),
    default=None,
    help="Path to configuration file (default: config.toml in current directory)",
)
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
@click.option("--cut-power", type=int, default=255, help="Cut layer power (0-255, default: 255)")
@click.option(
    "--unit",
    "-u",
    type=click.Choice(["mm", "in"], case_sensitive=False),
    default="mm",
    help="Unit of measurement (default: mm)",
)
@click.option("--passes", "-p", type=int, default=1, help="Number of passes (default: 1)")
@click.option("--pass-depth", type=float, default=1, help="Pass depth (unit, default: 1)")
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
@click.option("--bed-width", type=float, default=200, help="Bed X width (unit, default: 200)")
@click.option("--bed-height", type=float, default=200, help="Bed Y length (unit, default: 200)")
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
@click.option("--scaling-factor", type=float, default=1, help="G-code scaling factor (default: 1)")
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
    config_file: str | None,
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

    # Load configuration file if available
    file_config = None
    try:
        file_config = load_config(config_file)
    except FileNotFoundError:
        # Config file not found, use CLI defaults
        pass
    except Exception as e:
        click.echo(f"Error loading configuration file: {e}", err=True)
        sys.exit(1)

    # Load header and footer files
    header = []
    if header_file:
        with open(header_file) as f:
            header = f.read().splitlines()

    footer = []
    if footer_file:
        with open(footer_file) as f:
            footer = f.read().splitlines()

    # Create configuration from file or CLI arguments
    if file_config:
        # Merge config file with CLI arguments (CLI overrides)
        cli_args_dict = {
            "travel_speed": travel_speed,
            "engrave_cutting_speed": engrave_cutting_speed,
            "engrave_power": engrave_power,
            "cut_cutting_speed": cut_cutting_speed,
            "cut_power": cut_power,
            "unit": unit,
            "passes": passes,
            "pass_depth": pass_depth,
            "dwell_time": dwell_time,
            "approximation_tolerance": approximation_tolerance,
            "tool_off_command": tool_off_command,
            "machine_origin": machine_origin,
            "zero_machine": zero_machine,
            "invert_y_axis": invert_y_axis,
            "use_document_size": use_document_size,
            "bed_width": bed_width,
            "bed_height": bed_height,
            "horizontal_offset": horizontal_offset,
            "vertical_offset": vertical_offset,
            "scaling_factor": scaling_factor,
            "z_axis_start": z_axis_start,
            "do_z_axis_start": do_z_axis_start,
            "move_to_origin_end": move_to_origin_end,
            "do_laser_off_start": do_laser_off_start,
            "do_laser_off_end": do_laser_off_end,
        }
        combine_config = merge_config_with_cli(file_config, cli_args_dict)
        # Override header/footer if provided via CLI
        if header:
            combine_config.header = header
        if footer:
            combine_config.footer = footer
        config = combine_config
    else:
        # Use CLI arguments only
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


# Entry point wrapper to allow direct invocation without "main" subcommand
def entry_point():
    """Entry point that allows calling main command directly."""
    import sys

    # If first argument is "config", use the group
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        cli()
    else:
        # Otherwise, find and invoke the main command
        # The main command is the one without a name (or with name matching the function)
        main_cmd = None
        for name, cmd in cli.commands.items():
            # Find the command that's not "config" - that's our main command
            if name != "config":
                main_cmd = cmd
                break

        if main_cmd:
            # Invoke the main command directly
            main_cmd()
        else:
            # Fallback to group (will show help)
            cli()


if __name__ == "__main__":
    entry_point()
