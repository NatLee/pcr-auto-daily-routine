from __future__ import annotations

import dataclasses
import logging

import pytest
from fakes import SETTINGS, FakeClock, FakeDesktop, Shown
from test_routine import DUNGEON_SCREENS, EXPLORER_SCREENS, FREE_GACHAPON_CLICKS, FREE_GACHAPON_SCREENS

from pcr_routine import cli
from pcr_routine.bot import Bot
from pcr_routine.device import DeviceError
from pcr_routine.routine import TASKS


@pytest.fixture
def fake_time(monkeypatch):
    """Make the real Bot use the pretend clock, the way the pretend desktop does."""
    clock = FakeClock()

    def bot(screen, pointer, templates, settings):
        return Bot(screen, pointer, templates, settings, clock=clock, sleep=clock.sleep)

    monkeypatch.setattr(cli, "Bot", bot)
    return clock


def run(argv, screens, clock):
    desktop = FakeDesktop(screens, clock)
    code = cli.main(argv, devices=lambda settings: (desktop, desktop))
    return code, desktop


def test_help_lists_every_task(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for name, task in TASKS.items():
        assert name in out and task.title in out
    assert "With no TASK it runs: free-gachapon explorer dungeon" in out


def test_unknown_task_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["dungeon", "arena"])
    assert exit_info.value.code == 2
    assert "unknown task arena (choose from free-gachapon, explorer" in capsys.readouterr().err


def test_no_task_runs_the_daily_routine_in_order(fake_time, caplog):
    caplog.set_level(logging.INFO)
    # Each task ends on the screen where the next one begins.
    screens = FREE_GACHAPON_SCREENS + EXPLORER_SCREENS + DUNGEON_SCREENS
    code, desktop = run([], screens, fake_time)
    assert code == 0
    assert desktop.clicked[:4] == FREE_GACHAPON_CLICKS
    assert desktop.clicked[-1] == "adventure-dungeon-ok.png"
    assert desktop.index == len(screens)
    assert "dungeon：完成" in caplog.text


def test_a_failed_task_does_not_stop_the_next_ones(fake_time):
    # Free 10-pull already used: gachapon gives up, explorer and dungeon still run.
    no_free_pull = [*FREE_GACHAPON_SCREENS[:2], Shown(("gachapon-common-after.png", "home-before.png"),
                                                       next="home-before.png")]
    screens = no_free_pull + EXPLORER_SCREENS[1:] + DUNGEON_SCREENS
    code, desktop = run([], screens, fake_time)
    assert code == 1
    assert desktop.clicked[-1] == "adventure-dungeon-ok.png"


def test_named_tasks_run_in_the_given_order(fake_time):
    code, desktop = run(["home", "home"], [Shown(("home-after.png",))], fake_time)
    assert code == 0
    assert desktop.clicked == []


def test_a_missing_image_is_reported_before_anything_is_clicked(tmp_path, capsys):
    def no_devices(settings):
        raise AssertionError("the desktop should not be touched")

    code = cli.main(["home"], settings=dataclasses.replace(SETTINGS, image_dir=tmp_path), devices=no_devices)
    assert code == 1
    assert "Button image not found" in capsys.readouterr().err


def test_a_device_problem_is_reported_plainly(capsys):
    def broken(settings):
        raise DeviceError("There is no monitor 5: pick 0 (all monitors) to 2.")

    assert cli.main(["home"], devices=broken) == 1
    assert "main.py: error: There is no monitor 5" in capsys.readouterr().err
