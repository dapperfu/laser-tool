# Examples

Sample SVGs for the `laser-gcode` CLI (`python -m laser` is the same command group).

```bash
laser-gcode config generate input.svg
laser-gcode layers input.svg
laser-gcode convert input.svg
```

One SVG writes `input.toml`. Convert uses that file, then `config.toml`. Generate with no SVG writes `config.toml`.

`config generate` always writes active `[global]`, `[cut]`, and `[engrave]` tables. Other Inkscape layers (for example `circle` in `demo_layers.svg`) are written commented out. Uncomment a table to include that layer in `convert`. Job order is engrave, then other enabled layers, then cut.

## Sample SVG files

- **`sample.svg`**: `cut` and `engrave` layers
- **`demo_layers.svg`**: eight named layers (`circle`, `square`, `triangle`, `ellipse`, `star`, `hexagon`, `line`, `polyline`)
- **`EngraveCut.svg`**: cut and engrave artwork
