# laser-tool

Fork of the [J Tech Photonics Laser Tool](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool). That project is an Inkscape extension that turns SVG paths into G-code for laser cutters and plotters. This repo keeps that extension and adds a standalone CLI.

Older J Tech releases and docs: [releases](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool/releases), [jtechphotonics.com](https://jtechphotonics.com/?page_id=2012). The conversion engine is the vendored [svg_to_gcode](https://github.com/PadLex/SvgToGcode) library.

## How it works

1. Read an SVG. Inkscape layers (`inkscape:groupmode="layer"`) are the job units.
2. Turn paths (and simple shapes) into curves, flip SVG Y into machine coordinates, then approximate curves as line segments.
3. Emit GRBL-style G-code: `G0` travel with the laser off, `G1` cuts, `M3 S…` / `M5` for power.

The CLI writes a TOML config from the SVG’s layer names, then converts only the layers you enable. `[cut]` and `[engrave]` are on by default; other layers are commented out until you uncomment them. Job order is engrave, then any other enabled layers, then cut last.

Inkscape still does a single pass from the dialog (optional one-layer filter) and can draw debug traces on the document.

Document units should be `mm` or `in` with scale `1`. Convert objects to paths if a layer comes out empty.

## CLI

```bash
pip install -e .
laser-gcode config generate drawing.svg
laser-gcode layers drawing.svg
laser-gcode convert drawing.svg
```

With one SVG, generate writes `drawing.toml` next to it. Convert looks for that file first, then `config.toml`. With no SVG, generate writes `config.toml`.

`python -m laser` is the same command group. Examples live in `examples/`.

## Inkscape

Clone this repo into your user extensions folder (Inkscape **Preferences → System** lists the path), then restart. Menu: **Extensions → Generate Laser Gcode → J Tech Community Laser Tool**.
