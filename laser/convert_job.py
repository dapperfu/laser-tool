"""Convert SVG layers to a combined G-code file using TOML config."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import click

from laser.config import CUT_DEFAULTS, ENGRAVE_DEFAULTS, EXTRA_LAYER_DEFAULTS, enabled_layer_names
from laser.converter import ConversionConfig, convert_svg_to_gcode
from laser.svg_layers import list_svg_layers


def is_empty_gcode(gcode_path: str) -> bool:
    """Return True if the file has no cutting commands."""
    try:
        with open(gcode_path) as f:
            lines = f.readlines()
    except OSError:
        return True

    cutting_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("G1", "G2", "G3", "M3 S")) and not stripped.startswith("G1 F"):
            cutting_lines += 1
    return cutting_lines == 0


def remove_gcode_footer(gcode_path: str) -> list[str]:
    """Remove trailing laser-off and return-to-origin footer lines."""
    with open(gcode_path) as f:
        lines = f.readlines()

    result = []
    in_footer = False
    for line in lines:
        stripped = line.strip()
        if stripped in {"M5", "M5;"}:
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
    """Return G-code after the unit command (skip duplicated header)."""
    with open(gcode_path) as f:
        lines = f.readlines()

    result = []
    found_unit = False
    for line in lines:
        stripped = line.strip()
        if stripped in {"G21", "G21;", "G20", "G20;"}:
            found_unit = True
            continue
        if found_unit:
            result.append(line.rstrip("\n"))
    return result


def layer_job_order(enabled: list[str], svg_layers: list[str]) -> list[str]:
    """
    Layers to process: enabled in config and present in the SVG.

    Order: engrave first, then other non-cut layers in config order, then cut last.
    """
    present = set(svg_layers)
    matching = [name for name in enabled if name in present]
    others = [name for name in matching if name not in {"engrave", "cut"}]
    ordered: list[str] = []
    if "engrave" in matching:
        ordered.append("engrave")
    ordered.extend(others)
    if "cut" in matching:
        ordered.append("cut")
    return ordered


def conversion_config_for_layer(config: dict, layer_name: str) -> ConversionConfig:
    """Build ConversionConfig from [global] plus a layer table."""
    global_config = config.get("global", {})
    layer_config = config.get(layer_name, {})

    if layer_name == "cut":
        defaults = CUT_DEFAULTS
    elif layer_name == "engrave":
        defaults = ENGRAVE_DEFAULTS
    else:
        defaults = EXTRA_LAYER_DEFAULTS

    cutting_speed = layer_config.get("cutting_speed", defaults["cutting_speed"])
    power = layer_config.get("power", defaults["power"])

    return ConversionConfig(
        unit=global_config.get("unit", "mm"),
        travel_speed=global_config.get("travel_speed", 3000),
        cutting_speed=cutting_speed,
        passes=global_config.get("passes", 1),
        pass_depth=global_config.get("pass_depth", 1),
        dwell_time=global_config.get("dwell_time", 0),
        approximation_tolerance=global_config.get("approximation_tolerance", 0.01),
        tool_power_command=f"M3 S{power};",
        tool_off_command=global_config.get("tool_off_command", "M5;"),
        machine_origin=global_config.get("machine_origin", "bottom-left"),
        zero_machine=global_config.get("zero_machine", False),
        invert_y_axis=global_config.get("invert_y_axis", False),
        use_document_size=global_config.get("use_document_size", True),
        bed_width=global_config.get("bed_width", 200),
        bed_height=global_config.get("bed_height", 200),
        horizontal_offset=global_config.get("horizontal_offset", 0),
        vertical_offset=global_config.get("vertical_offset", 0),
        scaling_factor=global_config.get("scaling_factor", 1),
        do_z_axis_start=global_config.get("do_z_axis_start", False),
        z_axis_start=global_config.get("z_axis_start", 0),
        move_to_origin_end=global_config.get("move_to_origin_end", False),
        do_laser_off_start=global_config.get("do_laser_off_start", True),
        do_laser_off_end=global_config.get("do_laser_off_end", True),
        layer_name=layer_name,
        header=global_config.get("header", []) if isinstance(global_config.get("header", []), list) else [],
        footer=global_config.get("footer", []) if isinstance(global_config.get("footer", []), list) else [],
    )


def generate_layer_gcode(svg_path: str, layer_name: str, config: dict, output_path: str) -> bool:
    """Generate G-code for one layer. Returns False on failure."""
    try:
        conversion_config = conversion_config_for_layer(config, layer_name)
        convert_svg_to_gcode(svg_path, output_path, conversion_config)
        return True
    except Exception:
        return False


def _strip_footer_lines(lines: list[str]) -> list[str]:
    result = []
    in_footer = False
    for line in lines:
        stripped = line.strip()
        if stripped in {"M5", "M5;"}:
            in_footer = True
            continue
        if in_footer and (stripped.startswith("G0 X0 Y0") or stripped.startswith("G0 X0 Y0 Z0")):
            continue
        if in_footer and stripped == "":
            continue
        if in_footer:
            in_footer = False
        result.append(line.rstrip("\n") if line.endswith("\n") else line)
    return result


def _body_after_header(lines: list[str]) -> list[str]:
    result = []
    found_unit = False
    for line in lines:
        stripped = line.strip()
        if stripped in {"G21", "G21;", "G20", "G20;"}:
            found_unit = True
            continue
        if found_unit:
            result.append(line.rstrip("\n") if line.endswith("\n") else line)
    return result


def combine_layer_gcode_files(layer_files: list[tuple[str, str]], output_path: str) -> None:
    """
    Combine per-layer G-code files.

    The first file keeps its header; later files skip the unit/header.
    Only the last file keeps the footer.
    """
    if not layer_files:
        raise ValueError("No layer G-code files to combine")

    if len(layer_files) == 1:
        Path(output_path).write_text(Path(layer_files[0][1]).read_text(encoding="utf-8"), encoding="utf-8")
        return

    with open(output_path, "w", encoding="utf-8") as outfile:
        last_index = len(layer_files) - 1
        for index, (layer_name, gcode_path) in enumerate(layer_files):
            raw = Path(gcode_path).read_text(encoding="utf-8").splitlines()
            if index == 0:
                lines = _strip_footer_lines(raw)
            elif index == last_index:
                lines = _body_after_header(raw)
            else:
                lines = _strip_footer_lines(_body_after_header(raw))

            for line in lines:
                outfile.write(line + "\n")

            if index != last_index:
                next_name = layer_files[index + 1][0]
                outfile.write("\n")
                outfile.write("; ==========================================\n")
                outfile.write(f"; Layer transition: {layer_name} -> {next_name}\n")
                outfile.write("; ==========================================\n")
                outfile.write("\n")


def convert_svg_layers(
    svg_path: str,
    output_path: str,
    config: dict,
    verbose: bool = True,
) -> tuple[bool, str | None]:
    """
    Convert enabled config layers that exist in the SVG into one G-code file.

    Returns (success, error_message).
    """
    svg_layers = list_svg_layers(svg_path)
    enabled = enabled_layer_names(config)
    ordered = layer_job_order(enabled, svg_layers)

    if not ordered:
        extra_hint = ""
        unused = [name for name in svg_layers if name not in enabled]
        if unused:
            extra_hint = (
                f"\nUncomment extra layer sections in the config to enable them (found in SVG: {', '.join(unused)})."
            )
        return (
            False,
            "No matching enabled layers between the config and SVG. "
            "Uncomment extra layer sections (e.g. [circle]) or add cut/engrave layers to the SVG." + extra_hint,
        )

    output_dir = os.path.dirname(output_path) or "."
    generated: list[tuple[str, str]] = []
    temp_paths: list[str] = []

    try:
        for layer_name in ordered:
            layer_cfg = config.get(layer_name, {})
            speed = layer_cfg.get("cutting_speed", "?")
            power = layer_cfg.get("power", "?")
            if verbose:
                click.echo(f"Generating layer '{layer_name}'...")
                click.echo(f"  Settings: cutting_speed={speed}, power=S{power}")

            with tempfile.NamedTemporaryFile(mode="w", suffix=".gcode", dir=output_dir, delete=False) as tmp:
                temp_path = tmp.name
            temp_paths.append(temp_path)

            success = generate_layer_gcode(svg_path, layer_name, config, temp_path)
            if not success:
                if verbose:
                    click.echo(f"  Failed to generate layer '{layer_name}', skipping")
                continue
            if is_empty_gcode(temp_path):
                if verbose:
                    click.echo(
                        f"  Warning: layer '{layer_name}' has no paths. "
                        "Convert objects to paths in Inkscape (Path → Object to Path)."
                    )
                continue
            generated.append((layer_name, temp_path))
            if verbose:
                click.echo(f"  Generated layer '{layer_name}'")

        if not generated:
            return (
                False,
                "No G-code was generated. Convert shapes to paths and confirm layer names match the config.",
            )

        combine_layer_gcode_files(generated, output_path)

        if verbose:
            click.echo("")
            click.echo(f"Output file: {output_path}")
            click.echo("Layers: " + ", ".join(name for name, _ in generated))

        return True, None
    except Exception as exc:
        return False, f"Failed to create combined G-code file: {exc}"
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.unlink(path)
