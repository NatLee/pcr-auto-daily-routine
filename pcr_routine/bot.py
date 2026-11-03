"""The moves a routine is made of: wait for a button, click it, go to a page, pause.

A task is a list of steps. It runs them in order and stops at the first one that
fails, the same way each hand-written action function used to return early.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Union

import numpy as np

from .config import Settings
from .device import Pointer, Screen
from .vision import Match, find

log = logging.getLogger(__name__)


class Bot:
    """Looks at the screen and clicks, with the button images loaded beforehand."""

    def __init__(
        self,
        screen: Screen,
        pointer: Pointer,
        templates: Mapping[str, np.ndarray],
        settings: Settings,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.screen = screen
        self.pointer = pointer
        self.templates = templates
        self.settings = settings
        self._clock = clock
        self._sleep = sleep

    def look(self, image: str) -> Match | None:
        """One screenshot, one search. The match is in desktop coordinates."""
        frame = self.screen.grab()
        match = find(frame.image, self.templates[image], self.settings.match_threshold)
        return None if match is None else match.moved(frame.left, frame.top)

    def wait_for(self, image: str, timeout: float) -> Match | None:
        """Keep looking until the button shows up or ``timeout`` seconds have passed.

        Always looks at least once, and once more right after the time is up.
        """
        log.info("等待 %s（最多 %g 秒）", image, timeout)
        start = self._clock()
        match = self.look(image)
        while match is None and self._clock() - start <= timeout:
            match = self.look(image)
        elapsed = self._clock() - start
        if match is not None:
            log.info("找到 %s（%.1f 秒）", image, elapsed)
        else:
            log.info("等不到 %s（%.1f 秒）", image, elapsed)
        return match

    def click(self, match: Match, *, pause_before: float = 0.0, pause_after: float = 0.0) -> None:
        x, y = match.center
        self.pointer.click(x, y, pause_before=pause_before, pause_after=pause_after)

    def pause(self, seconds: float) -> None:
        self._sleep(seconds)


@dataclass(frozen=True)
class Click:
    """Wait for a button and click its centre."""

    image: str
    label: str
    timeout: float | None = None
    """Seconds to look for the button; ``None`` means ``Settings.wait_timeout``."""
    pause_before: float = 0.0
    """Seconds between moving the mouse onto the button and clicking it."""
    pause_after: float = 0.0
    """Seconds to wait after the click, once the cursor is back."""
    optional: bool = False
    """If true, a button that never shows up does not stop the task."""
    missing: str | None = None
    """What to log when the button never shows up; defaults to 找不到<label>."""

    def images(self) -> Iterator[str]:
        yield self.image

    def run(self, bot: Bot) -> bool:
        timeout = bot.settings.wait_timeout if self.timeout is None else self.timeout
        match = bot.wait_for(self.image, timeout)
        if match is None:
            log.info(self.missing or f"找不到{self.label}")
            return self.optional
        bot.click(match, pause_before=self.pause_before, pause_after=self.pause_after)
        log.info("已點擊%s", self.label)
        return True


@dataclass(frozen=True)
class Switch:
    """Go to a page with a tab-like button that looks different once you are there.

    Click the ``before`` look, then expect the ``after`` look. If only the ``after``
    look is on screen, we are already on that page and nothing is clicked.
    """

    before: str
    after: str
    label: str

    def images(self) -> Iterator[str]:
        yield self.before
        yield self.after

    def run(self, bot: Bot) -> bool:
        settings = bot.settings
        log.info("前往%s", self.label)
        match = bot.wait_for(self.before, settings.switch_before_timeout)
        if match is None:
            log.info("這個畫面沒有%s的入口，看看是不是已經在%s", self.label, self.label)
        else:
            bot.click(match)
            log.info("已點擊%s", self.label)
        if bot.wait_for(self.after, settings.switch_after_timeout) is None:
            log.info("沒有到%s", self.label)
            return False
        log.info("已經在%s", self.label)
        return True


@dataclass(frozen=True)
class Pause:
    """Wait a fixed time, e.g. for an animation to finish."""

    seconds: float
    reason: str = ""

    def images(self) -> Iterator[str]:
        return iter(())

    def run(self, bot: Bot) -> bool:
        if self.reason:
            log.info("%s（%g 秒）", self.reason, self.seconds)
        bot.pause(self.seconds)
        return True


Step = Union[Click, Switch, Pause]


@dataclass(frozen=True)
class Task:
    """A named list of steps, run in order until one fails."""

    name: str
    """What you type on the command line."""
    title: str
    """What the log calls it."""
    steps: tuple[Step, ...]

    def images(self) -> list[str]:
        return list(dict.fromkeys(image for step in self.steps for image in step.images()))

    def run(self, bot: Bot) -> bool:
        log.info("==== 執行%s（%s）", self.title, self.name)
        return all(step.run(bot) for step in self.steps)
