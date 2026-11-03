"""Find a button image on a screenshot. Plain functions: arrays in, positions out."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


class TemplateError(Exception):
    """A button image is missing or unreadable."""


@dataclass(frozen=True)
class Match:
    """Where a button was found, in the coordinates of the picture it was found in.

    ``score`` is the similarity at that spot (see ``Settings.match_threshold``).
    """

    left: int
    top: int
    width: int
    height: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        # Integer centre, rounded down: the spot the mouse clicks.
        return (2 * self.left + self.width) // 2, (2 * self.top + self.height) // 2

    def moved(self, dx: int, dy: int) -> Match:
        return Match(self.left + dx, self.top + dy, self.width, self.height, self.score)


def to_gray(image: np.ndarray) -> np.ndarray:
    """Turn a BGR or BGRA picture (what OpenCV and mss hand out) into one gray channel."""
    if image.ndim == 2:
        return image
    code = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
    return cv2.cvtColor(image, code)


def load_template(path: Path) -> np.ndarray:
    """Read a button image as gray pixels; any transparency is ignored.

    Reads the bytes with numpy and decodes them with OpenCV, because ``cv2.imread``
    cannot open paths with non-ASCII characters on Windows (a Chinese user name, say).
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except FileNotFoundError:
        raise TemplateError(f"Button image not found: {path}") from None
    except OSError as error:
        raise TemplateError(f"Cannot read button image {path}: {error.strerror}") from None
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise TemplateError(f"Not an image OpenCV can read: {path}")
    return to_gray(image)


def load_templates(folder: Path, names: Iterable[str]) -> dict[str, np.ndarray]:
    """Load every named image from ``folder`` up front, so a missing one fails before any click."""
    return {name: load_template(folder / name) for name in dict.fromkeys(names)}


def find(screen: np.ndarray, template: np.ndarray, threshold: float) -> Match | None:
    """Look for ``template`` on ``screen`` (both gray). ``None`` if nothing scores ``threshold``.

    Returns the first spot that qualifies, reading the scores row by row from the top
    left, so of two copies of a button the higher one wins. This is the rule the script
    has always used. Because it stops at the first qualifying spot rather than the best
    one, the box can sit a few pixels above or left of a perfect fit; its centre is still
    well inside the button.
    """
    height, width = template.shape[:2]
    if height > screen.shape[0] or width > screen.shape[1]:
        return None
    scores = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    rows, cols = np.nonzero(scores >= threshold)  # row by row, left to right
    if rows.size == 0:
        return None
    top, left = int(rows[0]), int(cols[0])
    return Match(left, top, width, height, float(scores[top, left]))
