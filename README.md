# J Tech Photonics Laser Tool - Fork

> **This is a fork of the [J Tech Photonics Laser Tool](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool) community version.**  
> This fork adds additional features and will be soft-forked into my own project for personal use. J Tech's upstream changes will be merged into this fork as they become available.

**Repository:** `https://github.com/dapperfu/laser-tool.git`

## What's New in This Fork

This fork extends the original J Tech Photonics Laser Tool with several enhancements:

- **Standalone CLI Tool**: Convert SVG to G-code from the command line without requiring the Inkscape GUI
- **Layer Selection**: Process specific layers from an SVG file (e.g., separate "cut" and "engrave" layers) for generating separate G-code files
- **Combine Cut & Engrave Tool**: Automatically combine cut and engrave layers into a single G-code file with different settings for each operation
- **"Use document size as bed size" Option**: Checkbox to automatically use document size as bed size, eliminating the need to enter dimensions twice
- **Self-contained Codebase**: Single `git clone` command works - no submodule initialization needed

---

# J Tech Photonics Laser Tool (Community version)
This Inkscape extension generates gcode for laser cutters and plotting machines from an SVG file.

The codebase is now fully self-contained. Simply clone the repository and you're ready to go - no submodule initialization required.

Version 2.0 just released and there are a lot of changes! If you want you can still access legacy releases (below 2.0) 
 on the [releases page](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool/releases).
Instructions for older versions can be found on [JTP's website](https://jtechphotonics.com/?page_id=2012).

This extension is essentially a UI wrapped around the [svg_to_gcode](https://github.com/PadLex/SvgToGcode) library. 
So if you want to learn how an Inkscape extension is structured, look no further.
If you're interested in peeking under the hood, check out svg_to_gcode.

## Installation

### Quick Install with Git Clone (Recommended)

The easiest way to install this fork is to clone it directly into your Inkscape extensions directory:

```bash
# Create the extensions directory if it doesn't exist (Linux)
mkdir -p ~/.config/inkscape/extensions

# Clone directly into the extensions directory
git clone https://github.com/dapperfu/laser-tool.git ~/.config/inkscape/extensions/laser
```

**For macOS:**
```bash
mkdir -p ~/Library/Application\ Support/Inkscape/extensions
git clone https://github.com/dapperfu/laser-tool.git ~/Library/Application\ Support/Inkscape/extensions/laser
```

**For Windows (Git Bash or WSL):**
```bash
mkdir -p "$APPDATA/inkscape/extensions"
git clone https://github.com/dapperfu/laser-tool.git "$APPDATA/inkscape/extensions/laser"
```

After cloning, restart Inkscape and the extension will be available at **Extension** > **Generate Laser Gcode** > **J Tech Community Laser Tool**.

### Alternative: Manual Installation

Download the latest release [here](https://github.com/JTechPhotonics/J-Tech-Photonics-Laser-Tool/releases/latest).
Inkscape versions below 1.0 are not supported. Use legacy releases if you are using Inkscape < 1.0.

Unzip `laser.zip` and copy the `laser` directly into the Inkscape **user extensions folder**. Inkscape lists the location
of your user extensions folder under **Edit/Inkscape** > **Preferences** > **System**.

Restart Inkscape and you're done.

## Tutorial

### Document Setup
Before using the extension, we need to make sure the document is setup correctly. Open **File** > **Document Properties**.

Set the document's **display units** to `mm` or `in`.
Then set **Scale x**, **Scale y** to `1` and **Viewbox > X**, **Viewbox > Y** to `0`.

<img src="./images/document_setup_properties.png" alt="document_setup_properties.png" width="600" />

Lastly, you can move and rescale your drawing to make it look like it did before. 

### Basic Usage

This extension will parse all svg paths and ignore everything else. 

**Step 1 is to convert all other shapes to paths.** In this case I want to convert the whole drawing to gcode.
So I select everything `ctr+A` and convert the drawing to paths 
**Path** > **Object to Path**.

Open the extension at **Extension** > **Generate Laser Gcode** > **J Tech Community Laser Tool**

Select the **same unit** you used in the **Document Settings**. Then choose an appropriate output directory and 
hit apply.

<img src="./images/important_settings.png" alt="important_settings.png" width="600" />

You'll notice two layers were added to your document:
* `debug reference points` contains the black corners. They 
represent the four corners of your machine's bed. You can use them to eyeball whether the gcode is scaled and placed 
correctly.
* `debug traces` contains the red paths which trace all generated gcode commands.

Note: debug layers are reset everytime you run the extension. So make sure you don't accidentally add any objects to them 
or they will be deleted.

## Layer Selection

You can process specific layers from an SVG file by specifying the layer name. This is useful when you have separate layers for different operations (e.g., "cut" and "engrave").

### In Inkscape Extension

1. In the extension dialog, go to the "Coordinate System and Transformations" tab
2. Enter the layer name in the "Layer Name" field (leave empty to process all layers)
3. The output filename will automatically include the layer name (e.g., `output_cut.gcode`)

### Using CLI Tool

```bash
# Process only the "cut" layer
python -m laser.cli input.svg --layer "cut" -o output_cut.gcode

# Process only the "engrave" layer
python -m laser.cli input.svg --layer "engrave" -o output_engrave.gcode
```

This allows you to generate separate G-code files for different operations from the same SVG file.

## Command-Line Interface

The tool includes a **standalone CLI** that can convert SVG files to G-code without requiring the Inkscape GUI. This is one of the key features added in this fork.

### Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

### Basic Usage

```bash
# Simple conversion (processes all layers)
python -m laser.cli input.svg -o output.gcode

# Process only a specific layer
python -m laser.cli input.svg --layer "cut" -o output_cut.gcode
python -m laser.cli input.svg --layer "engrave" -o output_engrave.gcode
```

### Engraving and Cutting from CLI

The CLI tool is particularly useful for generating separate G-code files for engraving and cutting operations from the same SVG file.

#### Engraving Example

```bash
# Generate G-code for engraving (low power, higher speed)
python -m laser.cli input.svg \
    --layer "engrave" \
    --travel-speed 3000 \
    --cutting-speed 1000 \
    --tool-power-command "M3 S75;" \
    --passes 1 \
    -o output_engrave.gcode
```

#### Cutting Example

```bash
# Generate G-code for cutting (high power, slower speed)
python -m laser.cli input.svg \
    --layer "cut" \
    --travel-speed 3000 \
    --cutting-speed 250 \
    --tool-power-command "M3 S255;" \
    --passes 1 \
    -o output_cut.gcode
```

#### Advanced Usage with Multiple Passes

```bash
# Multiple passes for precision cutting
python -m laser.cli input.svg \
    --layer "cut" \
    --travel-speed 5000 \
    --cutting-speed 1000 \
    --passes 3 \
    --pass-depth 0.5 \
    --tool-power-command "M3 S255;" \
    -o output_cut_multipass.gcode
```

### Combine Cut & Engrave Tool

This fork includes a specialized tool to automatically combine cut and engrave layers into a single G-code file with optimized settings for each operation:

```bash
# Combine cut and engrave layers with different settings
python -m laser.combine_cut_engrave input.svg \
    --engrave-cutting-speed 1000 \
    --engrave-power 75 \
    --cut-cutting-speed 250 \
    --cut-power 255 \
    --travel-speed 3000 \
    -o output_combined.gcode
```

Or use the installed command:
```bash
combine-cut-engrave input.svg \
    --engrave-cutting-speed 1000 \
    --engrave-power 75 \
    --cut-cutting-speed 250 \
    --cut-power 255 \
    -o output_combined.gcode
```

This tool automatically:
- Processes the "engrave" layer first with engraving settings
- Then processes the "cut" layer with cutting settings
- Combines both into a single G-code file ready for your laser cutter

### Available CLI Options

**Basic Options:**
- `--layer, -l`: Process only the specified layer (by Inkscape label)
- `--output, -o`: Output G-code file path
- `--unit, -u`: Unit of measurement (mm or in, default: mm)

**Speed & Power:**
- `--travel-speed, -t`: Travel speed (unit/min, default: 3000)
- `--cutting-speed, -c`: Cutting speed (unit/min, default: 750)
- `--tool-power-command`: Tool power command (e.g., "M3 S255;" for 100% power)
- `--tool-off-command`: Tool off command (default: "M5;")

**Passes & Depth:**
- `--passes, -p`: Number of passes (default: 1)
- `--pass-depth`: Pass depth (unit, default: 1)

**Machine Configuration:**
- `--machine-origin`: Machine origin (bottom-left, center, top-left, default: bottom-left)
- `--bed-width`: Bed X width (unit, default: 200)
- `--bed-height`: Bed Y length (unit, default: 200)
- `--use-document-size`: Use document size as bed size (default: False)
- `--zero-machine`: Zero machine coordinates (G92)
- `--invert-y-axis`: Invert Y-axis

**Advanced Options:**
- `--header-file`: Custom G-code header file
- `--footer-file`: Custom G-code footer file
- `--horizontal-offset`: G-code X offset (unit)
- `--vertical-offset`: G-code Y offset (unit)
- `--scaling-factor`: G-code scaling factor (default: 1)
- `--dwell-time`: Dwell time before moving (ms)
- `--approximation-tolerance`: Approximation tolerance (default: 0.01)

For a complete list of options, run:
```bash
python -m laser.cli --help
python -m laser.combine_cut_engrave --help
```

See the `examples/` directory for more usage examples and shell scripts demonstrating various workflows.

## Contribute

* As a user you can contribute by suggesting features, testing the library and reporting any bugs you encounter in a 
detailed issue.
* As a developer of any skill level you can make pull requests which close issues or introduce useful features. 
Just make sure to create an issue describing what features you want to add before taking the time to implement them.
