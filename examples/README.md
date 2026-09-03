# Examples

Scripts demonstrating the `laser-gcode` CLI (`python -m laser.cli` is the same command group).

## Running example scripts

From the project root:

```bash
./examples/basic_usage.sh
./examples/advanced_usage.sh
./examples/combine_cut_engrave.sh examples/sample.svg
./examples/demo_multi_layer_settings.sh
```

## Commands

```bash
python -m laser.cli config generate input.svg -o config.toml
python -m laser.cli layers input.svg
python -m laser.cli convert input.svg -c config.toml -o output.gcode
```

Or after `pip install -e .`:

```bash
laser-gcode config generate input.svg -o config.toml
laser-gcode convert input.svg -c config.toml -o output.gcode
```

`config generate` always writes active `[global]`, `[cut]`, and `[engrave]` tables. Other Inkscape layers (for example `circle` in `demo_layers.svg`) are written commented out. Uncomment a table to include that layer in `convert`. Job order is engrave, then other enabled layers, then cut.

## Sample SVG files

- **`sample.svg`**: `cut` and `engrave` layers
- **`demo_layers.svg`**: eight named layers (`circle`, `square`, `triangle`, `ellipse`, `star`, `hexagon`, `line`, `polyline`)
- **`EngraveCut.svg`**: cut and engrave artwork (if present)
- **`CelticFleurHair.svg`**: more complex cut/engrave example (if present)
