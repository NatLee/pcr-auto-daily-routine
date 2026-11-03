"""The only code that touches the real desktop: grabbing the screen and clicking the mouse.

Everything else talks to the two small interfaces below, so tests can hand in a
pretend desktop instead.
"""

from __future__ import annotations

import importlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol

import numpy as np

from .vision import to_gray


class DeviceError(Exception):
    """The screen or the mouse cannot be used."""


@dataclass(frozen=True)
class Frame:
    """One screenshot, in gray, plus where its top-left pixel sits on the desktop.

    With several monitors the desktop can start left of or above the main screen,
    so pixel (0, 0) of the picture is not always desktop position (0, 0).
    """

    image: np.ndarray
    left: int = 0
    top: int = 0


class Screen(Protocol):
    def grab(self) -> Frame: ...


class Pointer(Protocol):
    def click(self, x: int, y: int, *, pause_before: float = 0.0, pause_after: float = 0.0) -> None: ...


def _require(module: str) -> ModuleType:
    try:
        return importlib.import_module(module)
    except ImportError as error:
        raise DeviceError(
            f"The '{module}' package is not installed ({error}). Run: pip install -r requirements.txt"
        ) from None


class DesktopScreen:
    """Screenshots of one monitor, or of all of them, taken with mss."""

    def __init__(self, monitor: int) -> None:
        mss = _require("mss")
        self._error = mss.ScreenShotError
        try:
            self._mss = mss.mss()
        except self._error as error:
            raise DeviceError(f"Cannot take screenshots here: {error}") from None
        monitors = self._mss.monitors
        if not 0 <= monitor < len(monitors):
            raise DeviceError(
                f"There is no monitor {monitor}: pick 0 (all monitors) to {len(monitors) - 1}."
            )
        self._area = monitors[monitor]

    def grab(self) -> Frame:
        try:
            shot = self._mss.grab(self._area)
        except self._error as error:
            raise DeviceError(f"Screenshot failed: {error}") from None
        return Frame(to_gray(np.array(shot)), self._area["left"], self._area["top"])


class MousePointer:
    """Clicks with the mouse package, then puts the cursor back where it was."""

    def __init__(self, sleep: Callable[[float], None] = time.sleep) -> None:
        self._mouse = _require("mouse")
        self._sleep = sleep

    def click(self, x: int, y: int, *, pause_before: float = 0.0, pause_after: float = 0.0) -> None:
        mouse = self._mouse
        home = mouse.get_position()
        mouse.move(x, y, absolute=True)
        if pause_before:
            self._sleep(pause_before)
        mouse.click(button="left")
        mouse.move(*home, absolute=True)
        if pause_after:
            self._sleep(pause_after)
