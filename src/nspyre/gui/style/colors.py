"""
Color palette. Some colors from https://gist.github.com/mishelen/9525865.

Copyright (c) 2022, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from collections import OrderedDict

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

colors = OrderedDict(
    [
        ('r', pomegranate),
        ('g', nephritis),
        ('b', belize_hole),
        ('c', green_sea),
        ('m', amethyst),
        ('y', sun_flower),
        ('k', wet_asphalt),
        ('w', clouds),
        ('o', orange),
        ('gr', concrete),
        ('red', pomegranate),
        ('green', nephritis),
        ('blue', belize_hole),
        ('cyan', green_sea),
        ('magenta', amethyst),
        ('yellow', sun_flower),
        ('black', blackish),
        ('white', clouds),
        ('orange', orange),
        ('gray', concrete),
    ]
)

cyclic_colors = [
    colors['r'],
    colors['g'],
    colors['b'],
    colors['m'],
    colors['c'],
    colors['w'],
    colors['y'],
    colors['o'],
    colors['gr'],
]
