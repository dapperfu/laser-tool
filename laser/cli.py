"""
Command-line interface for SVG to G-code conversion.

Usage:
    laser-gcode config generate [SVG...] [-o drawing.toml]
    laser-gcode config validate [-c config.toml]
    laser-gcode layers SVG
    laser-gcode convert SVG [-c drawing.toml] [-o out.gcode]
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*Compile with an empty body.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*empty body.*")

laser_dir = Path(__file__).parent
if str(laser_dir) not in sys.path:
    sys.path.insert(0, str(laser_dir))

import click

try:
    from laser.inkscape_paths import add_inkscape_paths

    add_inkscape_paths()
except ImportError:
    pass

from laser.config import (
    default_generate_config_path,
    find_config_file,
    generate_config_from_svgs,
    load_config,
    validate_config,
)
from laser.convert_job import convert_svg_layers
from laser.svg_layers import list_svg_layers


@click.group()
def cli():
    """Convert SVG files to laser G-code using a TOML config."""


@cli.group("config")
def config_group():
    """Configuration management commands."""


@config_group.command("generate")
@click.argument("svg_files", nargs=-1, type=click.Path(exists=True, readable=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Path to write (default: <svg>.toml next to one SVG, otherwise config.toml)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite an existing configuration file without prompting",
)
def config_generate(svg_files: tuple[str, ...], output: str | None, force: bool) -> None:
    """Generate a config file from SVG layer names.

    Always writes [global], [cut], and [engrave]. Other layers found in the
    SVG(s) are written as commented-out tables (uncomment to enable).
    """
    config_path = Path(output) if output else default_generate_config_path(svg_files)

    if config_path.exists() and not force:
        if not click.confirm(f"Configuration file exists at {config_path}. Overwrite?"):
            click.echo("Aborted.")
            return

    content = generate_config_from_svgs(list(svg_files) if svg_files else None)
    config_path.write_text(content, encoding="utf-8")
    click.echo(f"Configuration file generated at {config_path}")
    if "# Additional layers from the SVG" in content:
        click.echo("Extra layers are commented out; uncomment a section to enable it.")


@config_group.command("validate")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Path to configuration file to validate",
)
def config_validate(config: str | None) -> None:
    """Validate a configuration file."""
    config_path = find_config_file(config)
    if config_path is None:
        click.echo("Error: Configuration file not found.", err=True)
        sys.exit(1)

    try:
        config_data = load_config(str(config_path))
        validate_config(config_data)
        click.echo(f"Configuration file {config_path} is valid.")
    except Exception as exc:
        click.echo(f"Error: Configuration file is invalid: {exc}", err=True)
        sys.exit(1)


@cli.command("layers")
@click.argument("svg_file", type=click.Path(exists=True, readable=True))
def layers_cmd(svg_file: str) -> None:
    """List Inkscape layer labels in an SVG."""
    labels = list_svg_layers(svg_file)
    if not labels:
        click.echo("No Inkscape layers found.")
        return
    for label in labels:
        click.echo(label)


@cli.command("convert")
@click.argument("svg_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, readable=True),
    default=None,
    help="Path to configuration file (default: <svg>.toml, then config.toml)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output G-code file path (default: input filename with .gcode extension)",
)
def convert_cmd(svg_file: str, config: str | None, output: str | None) -> None:
    """Convert SVG layers to G-code using a TOML config."""
    try:
        resolved_config = find_config_file(config, svg_path=svg_file)
        file_config = load_config(config, svg_path=svg_file)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Error loading configuration file: {exc}", err=True)
        sys.exit(1)

    output_path = output if output else str(Path(svg_file).with_suffix(".gcode"))

    click.echo(f"Input SVG:  {svg_file}")
    click.echo(f"Config:     {resolved_config}")
    click.echo(f"Output:     {output_path}")
    click.echo("")

    success, error_message = convert_svg_layers(svg_file, output_path, file_config)
    if not success:
        click.echo(f"Error: {error_message}", err=True)
        sys.exit(1)


def entry_point():
    """Installed console script entry point."""
    cli()


if __name__ == "__main__":
    cli()
