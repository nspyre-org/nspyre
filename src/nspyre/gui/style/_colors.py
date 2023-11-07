"""
Color palette.
"""
from typing import Dict

import numpy as np


def avg_colors(color_a: tuple, color_b: tuple):
    """Average two colors by RGB value.

    Args:
        color_a: first color
        color_b: second color

    Returns:
        averaged color as a tuple
    """
    return tuple(np.average((color_a, color_b), axis=0).astype(int))


dark_grey = (53, 53, 53)
grey = (70, 70, 70)
almost_white = (240, 240, 240)
green_sea = (22, 160, 133)
nephritis = (39, 174, 96)
belize_hole = (41, 128, 185)
amethyst = (155, 89, 182)
wet_asphalt = (52, 73, 94)
orange = (243, 156, 18)
sun_flower = (241, 196, 15)
pumpkin = (211, 84, 0)
pomegranate = (192, 57, 43)
clouds = (236, 240, 241)
concrete = (149, 165, 166)
blackish = (24, 24, 24)

colors: Dict = {
    'r': pomegranate,
    'g': nephritis,
    'b': belize_hole,
    'c': green_sea,
    'm': amethyst,
    'y': sun_flower,
    'k': wet_asphalt,
    'w': clouds,
    'o': orange,
    'gr': concrete,
    'red': pomegranate,
    'green': nephritis,
    'blue': belize_hole,
    'cyan': green_sea,
    'magenta': amethyst,
    'yellow': sun_flower,
    'black': blackish,
    'white': clouds,
    'orange': orange,
    'gray': concrete,
}
"""List of colors from
`<https://gist.github.com/mishelen/9525865>`_."""

cyclic_colors = [
    (0.12156, 0.46666, 0.70588),  # blue
    (1.00000, 0.49803, 0.05490),  # orange
    (0.17254, 0.62745, 0.17254),  # green
    (0.58039, 0.40392, 0.74117),  # purple
    (0.54901, 0.33725, 0.29411),  # brown
    (0.89019, 0.46666, 0.76078),  # pink
    (0.49803, 0.49803, 0.49803),  # grey
    (0.83921, 0.15294, 0.15686),  # red
    (0.65098, 0.85882, 0.07058),  # lime
    (0.09019, 0.74509, 0.81176),  # cyan
]
"""List of colors for plotting based on
`Tableau <https://matplotlib.org/stable/gallery/color/named_colors.html>`_."""
