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

### Using the CLI

Generate a TOML config from the SVG, edit layer speed/power, then convert. Only uncommented layer tables that exist in the SVG are processed (`engrave` first, then other layers, `cut` last).

```bash
laser-gcode config generate input.svg -o config.toml
laser-gcode convert input.svg -c config.toml -o output.gcode
```

`python -m laser.cli` is the same command group.

## Command-Line Interface

The installed command is **`laser-gcode`**. Machine and per-layer settings live in TOML, not in a long flag list.

```text
laser-gcode config generate [SVG...] [-o config.toml] [--force]
laser-gcode config validate [-c config.toml]
laser-gcode layers SVG
laser-gcode convert SVG [-c config.toml] [-o out.gcode]
```

### Installation

```bash
pip install -e .
```

### Generate a config from SVG layers

```bash
# Canonical [global], [cut], and [engrave] are always written (active).
# Any other Inkscape layer is written as a commented-out table.
laser-gcode config generate examples/sample.svg -o config.toml
laser-gcode config generate examples/demo_layers.svg -o demo.toml
```

For `demo_layers.svg` the file includes commented sections such as `[circle]`, `[square]`, and the rest. Uncomment a section to enable that layer. Cut and engrave stay active; they are skipped at convert time if the SVG does not contain those layers.

```toml
# [circle]
# cutting_speed = 750.0
# power = 128
```

### Convert

```bash
laser-gcode convert examples/sample.svg -c config.toml -o output.gcode
```

If no extra layers are uncommented and the SVG has no `cut`/`engrave` layers, convert exits with an error telling you to uncomment sections (for example `[circle]`).

List layer names:

```bash
laser-gcode layers examples/demo_layers.svg
```

Validate a config:

```bash
laser-gcode config validate -c config.toml
```

See the `examples/` directory for scripts that follow this workflow.

## Contribute

* As a user you can contribute by suggesting features, testing the library and reporting any bugs you encounter in a 
detailed issue.
* As a developer of any skill level you can make pull requests which close issues or introduce useful features. 
Just make sure to create an issue describing what features you want to add before taking the time to implement them.
