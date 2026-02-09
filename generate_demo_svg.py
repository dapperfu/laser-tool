#!/usr/bin/env python3
"""
Generate a demo SVG file with multiple objects on separate Inkscape layers.

This script creates an SVG file with various shapes (circles, squares, triangles, etc.)
each on its own layer to demonstrate how the CLI tool works with layer selection.
"""

import sys
import click
from pathlib import Path


def create_svg_content() -> str:
    """Generate SVG content with multiple objects on separate layers."""
    
    # SVG header with Inkscape namespace
    svg_header = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="200mm" 
     height="200mm" 
     viewBox="0 0 200 200">
'''
    
    layers = []
    
    # Layer 1: Circle
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="circle" id="layer_circle">
    <circle cx="50" cy="50" r="30" fill="none" stroke="red" stroke-width="1"/>
  </g>''')
    
    # Layer 2: Square
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="square" id="layer_square">
    <rect x="120" y="20" width="60" height="60" fill="none" stroke="blue" stroke-width="1"/>
  </g>''')
    
    # Layer 3: Triangle
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="triangle" id="layer_triangle">
    <path d="M 50,120 L 20,180 L 80,180 Z" fill="none" stroke="green" stroke-width="1"/>
  </g>''')
    
    # Layer 4: Ellipse
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="ellipse" id="layer_ellipse">
    <ellipse cx="150" cy="120" rx="40" ry="25" fill="none" stroke="purple" stroke-width="1"/>
  </g>''')
    
    # Layer 5: Star (pentagon)
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="star" id="layer_star">
    <path d="M 50,150 L 55,165 L 70,165 L 58,175 L 63,190 L 50,180 L 37,190 L 42,175 L 30,165 L 45,165 Z" 
          fill="none" stroke="orange" stroke-width="1"/>
  </g>''')
    
    # Layer 6: Hexagon
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="hexagon" id="layer_hexagon">
    <path d="M 120,150 L 135,140 L 150,150 L 150,170 L 135,180 L 120,170 Z" 
          fill="none" stroke="cyan" stroke-width="1"/>
  </g>''')
    
    # Layer 7: Line
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="line" id="layer_line">
    <line x1="20" y1="20" x2="100" y2="100" stroke="magenta" stroke-width="2"/>
  </g>''')
    
    # Layer 8: Polyline
    layers.append('''  <g inkscape:groupmode="layer" inkscape:label="polyline" id="layer_polyline">
    <polyline points="150,50 160,60 170,50 180,60 190,50" fill="none" stroke="brown" stroke-width="1"/>
  </g>''')
    
    # Combine all parts
    svg_content = svg_header + '\n'.join(layers) + '\n</svg>'
    
    return svg_content


@click.command()
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="examples/demo_layers.svg",
    help="Output SVG file path (default: examples/demo_layers.svg)"
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing file (default: False)"
)
def main(output: str, overwrite: bool) -> None:
    """
    Generate a demo SVG file with multiple objects on separate Inkscape layers.
    
    This creates an SVG file with various shapes (circles, squares, triangles, etc.)
    each on its own layer. You can use this to test the CLI tool's layer selection
    functionality with commands like:
    
        python -m laser.cli demo_layers.svg --layer "circle"
        python -m laser.cli demo_layers.svg --layer "square"
    """
    output_path = Path(output)
    
    # Check if file exists
    if output_path.exists() and not overwrite:
        click.echo(f"Error: File {output_path} already exists. Use --overwrite to replace it.", err=True)
        click.echo(f"  python {Path(__file__).name} -o {output_path} --overwrite")
        sys.exit(1)
    
    # Generate SVG content
    svg_content = create_svg_content()
    
    # Write to file
    try:
        output_path.write_text(svg_content, encoding="utf-8")
        click.echo(f"✓ Successfully created {output_path}")
        click.echo(f"\nGenerated SVG with the following layers:")
        click.echo("  - circle: Red circle")
        click.echo("  - square: Blue square")
        click.echo("  - triangle: Green triangle")
        click.echo("  - ellipse: Purple ellipse")
        click.echo("  - star: Orange star")
        click.echo("  - hexagon: Cyan hexagon")
        click.echo("  - line: Magenta line")
        click.echo("  - polyline: Brown polyline")
        click.echo(f"\nYou can test the CLI tool with:")
        click.echo(f"  python -m laser.cli {output_path} --layer \"circle\" -o output_circle.gcode")
        click.echo(f"  python -m laser.cli {output_path} --layer \"square\" -o output_square.gcode")
    except Exception as e:
        click.echo(f"Error writing file: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    import sys
    main()
