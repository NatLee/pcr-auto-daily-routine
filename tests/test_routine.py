"""Each task played through on the pretend game, checking what gets clicked and in which order.

The expected orders and pauses are the ones the original hand-written action functions had.
"""

from __future__ import annotations

import logging

import pytest
from fakes import SETTINGS, FakeClock, FakeDesktop, Shown, make_bot, path

from pcr_routine.bot import Switch
from pcr_routine.routine import DAILY_ROUTINE, TASKS
from pcr_routine.vision import find, load_templates

FREE_GACHAPON_SCREENS = [
    Shown(("gachapon-before.png",), next="gachapon-before.png"),
    Shown(("gachapon-after.png", "gachapon-common-before.png"), next="gachapon-common-before.png"),
    Shown(("gachapon-common-after.png", "gachapon-10-free.png"), next="gachapon-10-free.png"),
    *path("OK.png"),
]
FREE_GACHAPON_CLICKS = ["gachapon-before.png", "gachapon-common-before.png", "gachapon-10-free.png", "OK.png"]

TO_ADVENTURE = [
    Shown(("home-before.png",), next="home-before.png"),
    Shown(("home-after.png", "adventure-before.png"), next="adventure-before.png"),
]

EXPLORER_STEPS = [
    "adventure-explorer.png",
    "adventure-explorer-exp.png",
    "adventure-explorer-exp-lv.png",
    "adventure-explorer-exp-lv.png",
    "adventure-explorer-lv-use-2.png",
    "OK.png",
    "adventure-explorer-exp-go-mana.png",
    "adventure-explorer-mana-lv.png",
    "adventure-explorer-lv-use-2.png",
    "back-explorer.png",
]
EXPLORER_SCREENS = [
    *TO_ADVENTURE,
    Shown(("adventure-after.png", EXPLORER_STEPS[0]), next=EXPLORER_STEPS[0]),
    *path(*EXPLORER_STEPS[1:]),
]

DUNGEON_STEPS = [
    "adventure-dungeon.png",
    "adventure-dungeon-extreme-v.png",
    "adventure-dungeon-skip.png",
    "adventure-dungeon-ok.png",
]
DUNGEON_SCREENS = [
    *TO_ADVENTURE,
    Shown(("adventure-after.png", DUNGEON_STEPS[0]), next=DUNGEON_STEPS[0]),
    *path(*DUNGEON_STEPS[1:]),
]


def play(task_name: str, screens, clock=None) -> tuple[bool, FakeDesktop]:
    task = TASKS[task_name]
    desktop = FakeDesktop(screens, clock or FakeClock())
    return task.run(make_bot(desktop, task.images())), desktop


def test_daily_routine_is_the_original_order():
    assert DAILY_ROUTINE == ("free-gachapon", "explorer", "dungeon")
    assert set(DAILY_ROUTINE) <= set(TASKS)


def test_free_gachapon():
    done, desktop = play("free-gachapon", FREE_GACHAPON_SCREENS)
    assert done
    assert desktop.clicked == FREE_GACHAPON_CLICKS
    assert [c.pause_before for c in desktop.clicks] == [0, 0, 2, 0]  # 2 s before the free 10-pull
    assert desktop.clock.sleeps == [3]


def test_free_gachapon_already_used_today(caplog):
    caplog.set_level(logging.INFO)
    done, desktop = play("free-gachapon", FREE_GACHAPON_SCREENS[:2] + [Shown(("gachapon-common-after.png",))])
    assert not done
    assert desktop.clicked == FREE_GACHAPON_CLICKS[:2]
    assert desktop.clock.sleeps == []  # no settling pause after a failed task
    assert "找不到或是已使用過免費轉蛋" in caplog.text


def test_free_gachapon_when_already_on_the_gachapon_page():
    screens = [Shown(("gachapon-after.png", "gachapon-common-after.png", "gachapon-10-free.png"),
                     next="gachapon-10-free.png"), *path("OK.png")]
    done, desktop = play("free-gachapon", screens)
    assert done
    assert desktop.clicked == ["gachapon-10-free.png", "OK.png"]


def test_explorer():
    done, desktop = play("explorer", EXPLORER_SCREENS)
    assert done
    assert desktop.clicked == ["home-before.png", "adventure-before.png", *EXPLORER_STEPS]
    assert desktop.clock.sleeps == [5, 3]  # the animation, then settling
    assert all(c.pause_before == c.pause_after == 0 for c in desktop.clicks)


def test_explorer_stops_when_a_step_is_missing():
    screens = EXPLORER_SCREENS[:4]  # up to the EXP adventure, then nothing
    done, desktop = play("explorer", screens + [Shown()])
    assert not done
    assert desktop.clicked == ["home-before.png", "adventure-before.png", *EXPLORER_STEPS[:2]]


def test_dungeon():
    done, desktop = play("dungeon", DUNGEON_SCREENS)
    assert done
    assert desktop.clicked == ["home-before.png", "adventure-before.png", *DUNGEON_STEPS]
    assert [c.pause_after for c in desktop.clicks] == [0, 0, 2, 2, 0, 0]
    assert desktop.clock.sleeps == [3]


def test_dungeon_waits_up_to_20_seconds_for_the_result():
    late_ok = Shown(("adventure-dungeon-ok.png",), next="adventure-dungeon-ok.png", appear_after=15)
    done, desktop = play("dungeon", DUNGEON_SCREENS[:-1] + [late_ok])
    assert done
    assert desktop.clicked[-1] == "adventure-dungeon-ok.png"


def test_skip_scene_clicks_what_it_finds():
    done, desktop = play("skip-scene", path("menu.png", "skip-scene.png", "dialog-skip.png"))
    assert done
    assert desktop.clicked == ["menu.png", "skip-scene.png", "dialog-skip.png"]


def test_skip_scene_is_fine_with_nothing_to_skip():
    done, desktop = play("skip-scene", [Shown()])
    assert done
    assert desktop.clicked == []


@pytest.mark.parametrize(("screens", "expected"), [(path("skip-play.png"), True), ([Shown()], False)])
def test_click_skip(screens, expected):
    done, desktop = play("click-skip", screens)
    assert done is expected
    assert desktop.clicked == (["skip-play.png"] if expected else [])


def test_home():
    screens = [Shown(("home-before.png",), next="home-before.png"), Shown(("home-after.png",))]
    done, desktop = play("home", screens)
    assert done
    assert desktop.clicked == ["home-before.png"]


def test_every_image_the_routine_uses_is_in_the_repo():
    images = [image for task in TASKS.values() for image in task.images()]
    assert load_templates(SETTINGS.image_dir, images)


SWITCHES = sorted(
    {step for task in TASKS.values() for step in task.steps if isinstance(step, Switch)},
    key=lambda step: step.before,
)


@pytest.mark.parametrize("switch", SWITCHES, ids=lambda step: step.label)
def test_the_two_looks_of_a_tab_are_not_mistaken_for_each_other(switch):
    # Switch relies on telling "not on the page yet" from "on the page" apart.
    templates = load_templates(SETTINGS.image_dir, switch.images())
    for shown, wanted in [(switch.after, switch.before), (switch.before, switch.after)]:
        desktop = FakeDesktop([Shown((shown,))], FakeClock())
        assert find(desktop.grab().image, templates[wanted], SETTINGS.match_threshold) is None
