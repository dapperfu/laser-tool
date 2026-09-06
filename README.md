# laser-tool

Headless SVG-to-G-code for laser cutters. You do not need to launch Inkscape.

Fork of the [J Tech Photonics Laser Tool](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool) Inkscape extension. This repo adds a CLI so generate, configure, and convert run from the shell.

## Install

```bash
pip install git+https://github.com/dapperfu/laser-tool.git
```

Requires Python 3.10+.

## Use

```bash
laser-gcode config generate drawing.svg
laser-gcode layers drawing.svg
laser-gcode convert drawing.svg
```

`config generate` writes `drawing.toml` next to one SVG (`config.toml` if you pass no SVG). Edit speeds and power there. `convert` loads that sibling file first, then `config.toml`. `[cut]` and `[engrave]` are enabled by default; other layers are commented out until you uncomment them. Order is engrave, then other enabled layers, then cut.

`python -m laser` is the same command group. Sample SVGs are in `examples/`.

The original Inkscape extension is still here: clone into your user extensions folder and use **Extensions → Generate Laser Gcode → J Tech Community Laser Tool**.

## How it works

Inkscape layers (`inkscape:groupmode="layer"`) are the job units. Paths and simple shapes become curves, SVG Y is flipped to machine coordinates, and curves are approximated as line segments.

Output is GRBL-style G-code: `G0` travel with the laser off, `G1` cuts, `M3 S…` / `M5` for power.

Document units should be `mm` or `in` with scale `1`. If a layer is empty, convert objects to paths.

Conversion engine: vendored [svg_to_gcode](https://github.com/PadLex/SvgToGcode). Older J Tech docs: [releases](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool/releases), [jtechphotonics.com](https://jtechphotonics.com/?page_id=2012).
