#!/bin/bash
# Generate a config from demo_layers.svg, show the [circle] section, enable extra
# layers, and convert to one G-code file.
#
# Run from the project root or from examples/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

CLI=(python -m laser.cli)

if [ -f "examples/demo_layers.svg" ]; then
    SVG_FILE="examples/demo_layers.svg"
else
    echo "Error: examples/demo_layers.svg not found"
    exit 1
fi

CONFIG_FILE="examples/demo_layers.toml"
OUTPUT_FILE="examples/demo_layers.gcode"

echo "=========================================="
echo "Multi-layer config from demo_layers.svg"
echo "=========================================="

"${CLI[@]}" layers "$SVG_FILE"
"${CLI[@]}" config generate "$SVG_FILE" -o "$CONFIG_FILE" --force

echo ""
echo "Commented [circle] section in $CONFIG_FILE:"
grep -A 10 -F "# [circle]" "$CONFIG_FILE" || true

python - "$CONFIG_FILE" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
out = []
in_extra = False
for line in lines:
    if line.startswith("# Additional layers from the SVG"):
        in_extra = True
    if in_extra and (
        re.match(r"^# \[", line)
        or re.match(r"^# cutting_speed =", line)
        or re.match(r"^# power =", line)
    ):
        out.append(line[2:])
        continue
    if in_extra and line == "#":
        out.append("")
        continue
    out.append(line)
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

echo ""
echo "Uncommented extra layers (including circle). Converting..."
"${CLI[@]}" convert "$SVG_FILE" -c "$CONFIG_FILE" -o "$OUTPUT_FILE"
echo "Wrote $CONFIG_FILE and $OUTPUT_FILE"
