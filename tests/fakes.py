"""A pretend game for the tests: screens made of the real button images pasted on noise."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache

import numpy as np

from pcr_routine.bot import Bot
from pcr_routine.config import Settings
from pcr_routine.device import Frame
from pcr_routine.vision import load_template, load_templates

SETTINGS = Settings()
SCREEN_SIZE = (720, 1280)  # rows, columns
GAP = 24  # pixels between pasted buttons
GRAB_COST = 0.25  # pretend seconds one screenshot takes


@cache
def template(name: str) -> np.ndarray:
    return load_template(SETTINGS.image_dir / name)


def noise(seed: int = 0, size: tuple[int, int] = SCREEN_SIZE) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, size, dtype=np.uint8)


class FakeClock:
    """Time that only moves when something takes time: a screenshot, a pause, a sleep."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@dataclass(frozen=True)
class Shown:
    """One screen of the pretend game."""

    buttons: tuple[str, ...] = ()
    next: str | None = None
    """Clicking this button moves on to the next screen."""
    appear_after: float = 0.0
    """The buttons only show up this many seconds after the screen does."""


def path(*buttons: str) -> list[Shown]:
    """Screens that each show one button, and clicking it moves on."""
    return [Shown((name,), next=name) for name in buttons]


@dataclass(frozen=True)
class Clicked:
    button: str | None  # what was under the cursor
    x: int
    y: int
    pause_before: float = 0.0
    pause_after: float = 0.0


class FakeDesktop:
    """Both the screen and the mouse of the pretend game."""

    def __init__(self, screens: Iterable[Shown], clock: FakeClock, *,
                 origin: tuple[int, int] = (0, 0), seed: int = 0) -> None:
        self.screens = list(screens)
        self.clock = clock
        self.origin = origin
        self.index = 0
        self.shown_at = 0.0
        self.grabs = 0
        self.clicks: list[Clicked] = []
        self.background = noise(seed)
        self.layouts = [self._layout(screen.buttons) for screen in self.screens]

    @staticmethod
    def _layout(buttons: Sequence[str]) -> dict[str, tuple[int, int, int, int]]:
        """Place buttons left to right, wrapping into rows: name -> (left, top, width, height)."""
        rows, cols = SCREEN_SIZE
        x = y = GAP
        row_height = 0
        boxes = {}
        for name in buttons:
            height, width = template(name).shape
            if x + width + GAP > cols:
                x, y, row_height = GAP, y + row_height + GAP, 0
            boxes[name] = (x, y, width, height)
            x += width + GAP
            row_height = max(row_height, height)
        assert y + row_height <= rows, f"too many buttons for one screen: {buttons}"
        return boxes

    def _visible(self) -> dict[str, tuple[int, int, int, int]]:
        if self.index >= len(self.screens):
            return {}
        if self.clock.now - self.shown_at < self.screens[self.index].appear_after:
            return {}
        return self.layouts[self.index]

    def grab(self) -> Frame:
        self.clock.now += GRAB_COST
        self.grabs += 1
        image = self.background.copy()
        for name, (x, y, width, height) in self._visible().items():
            image[y:y + height, x:x + width] = template(name)
        return Frame(image, *self.origin)

    def click(self, x: int, y: int, *, pause_before: float = 0.0, pause_after: float = 0.0) -> None:
        self.clock.now += pause_before + pause_after
        local_x, local_y = x - self.origin[0], y - self.origin[1]
        hit = next((name for name, (left, top, width, height) in self._visible().items()
                    if left <= local_x < left + width and top <= local_y < top + height), None)
        self.clicks.append(Clicked(hit, x, y, pause_before, pause_after))
        if hit is not None and hit == self.screens[self.index].next:
            self.index += 1
            self.shown_at = self.clock.now

    @property
    def clicked(self) -> list[str | None]:
        return [click.button for click in self.clicks]


def make_bot(desktop: FakeDesktop, images: Iterable[str]) -> Bot:
    templates = load_templates(SETTINGS.image_dir, images)
    return Bot(desktop, desktop, templates, SETTINGS, clock=desktop.clock, sleep=desktop.clock.sleep)
