"""The knobs: where the button images live, how picky the matching is, how long to wait.

The routine itself (which buttons, in which order, and the few steps that wait longer
than usual) is in :mod:`pcr_routine.routine`. No other module has numbers or paths in it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    image_dir: Path = REPO_ROOT / "img"
    """Folder with the button images. They are matched at their pixel size, so the game
    window has to be as big as it was when the images were captured."""

    match_threshold: float = 0.7
    """How similar a spot on the screen must be to a button image (OpenCV's
    TM_CCOEFF_NORMED score, 1.0 = identical) before it counts as that button."""

    monitor: int = 0
    """Which screen to grab, as numbered by mss: 0 is every monitor as one picture,
    1 is the first monitor, 2 the second, and so on."""

    wait_timeout: float = 3.0
    """Seconds a step keeps looking for its button, unless the routine says otherwise."""

    switch_before_timeout: float = 3.0
    """Going to a page: seconds to look for the button that opens it."""

    switch_after_timeout: float = 2.0
    """Going to a page: seconds to look for the button that shows we are on it."""
