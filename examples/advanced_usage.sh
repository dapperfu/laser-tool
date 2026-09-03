#!/bin/bash
# Generate a config, inspect layers, and convert sample.svg.
#
# Run from the project root or from examples/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SVG_FILE="examples/sample.svg"
CONFIG="examples/sample_config.toml"
CLI=(python -m laser.cli)

if [ ! -f "$SVG_FILE" ]; then
    echo "Error: $SVG_FILE not found"
    exit 1
fi

echo "Layers in $SVG_FILE:"
"${CLI[@]}" layers "$SVG_FILE"

"${CLI[@]}" config generate "$SVG_FILE" -o "$CONFIG" --force
"${CLI[@]}" config validate -c "$CONFIG"
"${CLI[@]}" convert "$SVG_FILE" -c "$CONFIG" -o examples/output_combined.gcode
echo "Wrote $CONFIG and examples/output_combined.gcode"
