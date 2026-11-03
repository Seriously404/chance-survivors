"""Helper utility functions."""

import math
from typing import Tuple


def get_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate the Euclidean distance between two points.

    Args:
        x1: First point x coordinate.
        y1: First point y coordinate.
        x2: Second point x coordinate.
        y2: Second point y coordinate.

    Returns:
        The distance between the two points.
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_player_rotation(
    mouse_position: Tuple[float, float],
    screen_width: int,
    screen_height: int,
) -> float:
    """Calculate the player's rotation based on mouse position.

    Args:
        mouse_position: Tuple of (mouse_x, mouse_y) screen coordinates.
        screen_width: Width of the screen in pixels.
        screen_height: Height of the screen in pixels.

    Returns:
        The rotation angle in radians.
    """
    mouse_x, mouse_y = mouse_position

    direction_x = mouse_x - screen_width / 2
    direction_y = screen_height / 2 - mouse_y

    if direction_x == 0 and direction_y == 0:
        return 0.0

    return math.atan2(direction_y, direction_x)
