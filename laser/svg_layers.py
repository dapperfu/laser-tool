"""List Inkscape layer labels from SVG files."""

from pathlib import Path
from xml.etree import ElementTree

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
DEBUG_LAYER_LABELS = frozenset({"debug traces", "debug reference points"})


def list_svg_layers(svg_path: str | Path) -> list[str]:
    """
    Return Inkscape layer labels from an SVG, in document order.

    Layers are ``<g>`` elements with ``inkscape:groupmode="layer"``.
    Debug layers used by the Inkscape extension are omitted.
    """
    path = Path(svg_path)
    root = ElementTree.parse(path).getroot()
    labels: list[str] = []
    seen: set[str] = set()

    groupmode_attr = f"{{{INKSCAPE_NS}}}groupmode"
    label_attr = f"{{{INKSCAPE_NS}}}label"

    for element in root.iter():
        if element.get(groupmode_attr) != "layer":
            continue
        label = element.get(label_attr)
        if not label or label in DEBUG_LAYER_LABELS or label in seen:
            continue
        seen.add(label)
        labels.append(label)

    return labels


def list_layers_from_svgs(svg_paths: list[str] | list[Path]) -> list[str]:
    """
    Union of layer labels from one or more SVGs, first-seen order.
    """
    labels: list[str] = []
    seen: set[str] = set()
    for svg_path in svg_paths:
        for label in list_svg_layers(svg_path):
            if label not in seen:
                seen.add(label)
                labels.append(label)
    return labels
