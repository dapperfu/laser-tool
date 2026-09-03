#!/bin/bash
# Generate a config from sample.svg and convert cut + engrave layers.
#
# Run from the project root or from examples/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f "examples/sample.svg" ]; then
    SVG_FILE="examples/sample.svg"
else
    echo "Error: examples/sample.svg not found"
    exit 1
fi

CLI=(python -m laser.cli)

"${CLI[@]}" config generate "$SVG_FILE" -o examples/sample_config.toml --force
"${CLI[@]}" convert "$SVG_FILE" -c examples/sample_config.toml -o examples/output.gcode
echo "Wrote examples/sample_config.toml and examples/output.gcode"
