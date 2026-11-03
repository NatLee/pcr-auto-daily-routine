from __future__ import annotations

import logging

import pytest
from fakes import GRAB_COST, FakeClock, FakeDesktop, Shown, make_bot, path, template

from pcr_routine.bot import Click, Pause, Switch, Task


@pytest.fixture
def clock():
    return FakeClock()


def test_wait_for_finds_a_button_that_is_already_there(clock):
    desktop = FakeDesktop(path("OK.png"), clock)
    match = make_bot(desktop, ["OK.png"]).wait_for("OK.png", timeout=3)
    assert match is not None
    assert desktop.grabs == 1


def test_wait_for_keeps_looking_until_the_button_shows_up(clock):
    desktop = FakeDesktop([Shown(("OK.png",), appear_after=1.0)], clock)
    assert make_bot(desktop, ["OK.png"]).wait_for("OK.png", timeout=3) is not None
    assert desktop.grabs == 4  # 0.25, 0.5, 0.75 s: nothing yet; 1.0 s: there


def test_wait_for_gives_up_after_the_timeout_and_says_so(clock, caplog):
    # Regression: the original checked the result object itself, which is always true,
    # so its "Timeout" message never showed up.
    caplog.set_level(logging.INFO)
    desktop = FakeDesktop([Shown()], clock)
    assert make_bot(desktop, ["OK.png"]).wait_for("OK.png", timeout=3) is None
    # Looks once, then again while at most 3 s have passed: 0.25 s ... 3.0 s, plus 3.25 s.
    assert desktop.grabs == int(3 / GRAB_COST) + 1
    assert "等不到 OK.png" in caplog.text


def test_clicks_land_on_the_button_when_the_desktop_does_not_start_at_zero(clock):
    # Regression: with a monitor left of or above the main one, the screenshot of all
    # monitors starts at a negative desktop position; the original ignored that offset.
    desktop = FakeDesktop(path("OK.png"), clock, origin=(-1920, -200))
    bot = make_bot(desktop, ["OK.png"])
    match = bot.wait_for("OK.png", timeout=3)
    bot.click(match)
    assert desktop.clicked == ["OK.png"]
    assert desktop.clicks[0].x < 0 and desktop.clicks[0].y < 0


def test_click_step_passes_its_pauses_to_the_mouse(clock):
    desktop = FakeDesktop(path("OK.png"), clock)
    step = Click("OK.png", "OK", pause_before=2, pause_after=1)
    assert step.run(make_bot(desktop, step.images()))
    assert (desktop.clicks[0].pause_before, desktop.clicks[0].pause_after) == (2, 1)


def test_click_step_uses_the_default_timeout_unless_it_has_its_own(clock):
    late = [Shown(("OK.png",), next="OK.png", appear_after=4.0)]
    assert not Click("OK.png", "OK").run(make_bot(FakeDesktop(late, clock), ["OK.png"]))
    clock = FakeClock()
    assert Click("OK.png", "OK", timeout=5).run(make_bot(FakeDesktop(late, clock), ["OK.png"]))


def test_missing_click_step_fails_unless_optional(clock, caplog):
    caplog.set_level(logging.INFO)
    bot = make_bot(FakeDesktop([Shown()], clock), ["OK.png"])
    assert not Click("OK.png", "OK按鈕").run(bot)
    assert "找不到OK按鈕" in caplog.text
    assert Click("OK.png", "OK按鈕", optional=True).run(bot)
    assert not Click("OK.png", "OK按鈕", missing="用完了").run(bot)
    assert "用完了" in caplog.text


HOME = Switch("home-before.png", "home-after.png", "主頁")


def test_switch_clicks_the_tab_and_checks_it_arrived(clock):
    screens = [Shown(("home-before.png",), next="home-before.png"), Shown(("home-after.png",))]
    desktop = FakeDesktop(screens, clock)
    assert HOME.run(make_bot(desktop, HOME.images()))
    assert desktop.clicked == ["home-before.png"]


def test_switch_does_nothing_when_already_on_the_page(clock):
    desktop = FakeDesktop([Shown(("home-after.png",))], clock)
    assert HOME.run(make_bot(desktop, HOME.images()))
    assert desktop.clicked == []


def test_switch_fails_when_the_page_never_shows(clock):
    desktop = FakeDesktop([Shown(("home-before.png",), next="home-before.png"), Shown()], clock)
    assert not HOME.run(make_bot(desktop, HOME.images()))
    desktop = FakeDesktop([Shown()], FakeClock())
    assert not HOME.run(make_bot(desktop, HOME.images()))
    assert desktop.clicked == []


def test_task_stops_at_the_first_failed_step(clock):
    task = Task("t", "測試", (Click("OK.png", "OK"), Click("menu.png", "清單"), Pause(3)))
    desktop = FakeDesktop(path("menu.png"), clock)  # no OK on screen
    assert not task.run(make_bot(desktop, task.images()))
    assert desktop.clicked == []
    assert clock.sleeps == []


def test_task_lists_each_image_once_in_order():
    task = Task("t", "測試", (HOME, Click("OK.png", "OK"), Pause(1), Click("home-after.png", "x")))
    assert task.images() == ["home-before.png", "home-after.png", "OK.png"]


def test_fake_screens_hold_the_real_button_pixels(clock):
    desktop = FakeDesktop(path("OK.png"), clock)
    frame = desktop.grab()
    left, top, width, height = desktop.layouts[0]["OK.png"]
    assert (frame.image[top:top + height, left:left + width] == template("OK.png")).all()
