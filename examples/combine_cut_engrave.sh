#!/bin/bash
# Combine cut and engrave layers using a generated TOML config.
#
# Usage:
#   ./examples/combine_cut_engrave.sh input.svg [output.gcode]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

CLI=(python -m laser.cli)

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input.svg> [output.gcode]"
    exit 1
fi

SVG_FILE="$1"
if [ ! -f "$SVG_FILE" ]; then
    echo "Error: $SVG_FILE not found"
    exit 1
fi

if [ $# -ge 2 ]; then
    OUTPUT_FILE="$2"
else
    OUTPUT_FILE="${SVG_FILE%.svg}.gcode"
fi

CONFIG_FILE="$(mktemp --suffix=.toml)"
trap 'rm -f "$CONFIG_FILE"' EXIT

echo "Generating config from $SVG_FILE"
"${CLI[@]}" config generate "$SVG_FILE" -o "$CONFIG_FILE" --force
"${CLI[@]}" convert "$SVG_FILE" -c "$CONFIG_FILE" -o "$OUTPUT_FILE"
echo "Wrote $OUTPUT_FILE"
