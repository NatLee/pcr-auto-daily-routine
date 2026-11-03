"""The routine as data: every task, step by step, with the button image each step looks for.

Steps use the waits from :class:`~pcr_routine.config.Settings` unless they say otherwise
here. ``docs/images/src/routine.js`` (the task-flow picture in the README) is exported
from this table by ``docs/images/src/export_routine.py``; a test checks they agree.
"""

from __future__ import annotations

from .bot import Click, Pause, Switch, Task

# Pages reached through a tab-like button (the "before" and "after" looks of that button).
HOME = Switch("home-before.png", "home-after.png", "主頁")
ADVENTURE = Switch("adventure-before.png", "adventure-after.png", "冒險")
GACHAPON = Switch("gachapon-before.png", "gachapon-after.png", "轉蛋頁面")
NORMAL_GACHAPON = Switch("gachapon-common-before.png", "gachapon-common-after.png", "普通轉蛋")

# Buttons used by more than one task.
CONFIRM = Click("OK.png", "OK按鈕", timeout=5)
USE_2_TICKETS = Click("adventure-explorer-lv-use-2.png", "使用2張券按鈕")
SETTLE = Pause(3)  # after a task, before the next one starts

FREE_GACHAPON = Task("free-gachapon", "免費轉蛋", (
    GACHAPON,
    NORMAL_GACHAPON,
    Click("gachapon-10-free.png", "免費轉蛋按鈕", timeout=5, pause_before=2,
          missing="找不到或是已使用過免費轉蛋"),
    CONFIRM,
    SETTLE,
))

EXPLORER = Task("explorer", "探索", (
    HOME,
    ADVENTURE,
    Click("adventure-explorer.png", "探索按鈕"),
    Click("adventure-explorer-exp.png", "經驗值冒險按鈕"),
    Click("adventure-explorer-exp-lv.png", "經驗值冒險任務按鈕"),
    Click("adventure-explorer-exp-lv.png", "經驗值冒險任務按鈕"),  # yes, twice
    USE_2_TICKETS,
    CONFIRM,
    Pause(5, "等待動畫結束"),
    Click("adventure-explorer-exp-go-mana.png", "前往瑪娜冒險按鈕"),
    Click("adventure-explorer-mana-lv.png", "瑪娜冒險任務按鈕"),
    USE_2_TICKETS,
    Click("back-explorer.png", "返回探索TOP按鈕"),
    SETTLE,
))

DUNGEON = Task("dungeon", "地下城", (
    HOME,
    ADVENTURE,
    Click("adventure-dungeon.png", "地下城按鈕", pause_after=2),
    Click("adventure-dungeon-extreme-v.png", "地下城任務按鈕", pause_after=2),  # only EXTREME V
    Click("adventure-dungeon-skip.png", "跳過地下城任務按鈕"),
    Click("adventure-dungeon-ok.png", "地下城任務OK按鈕", timeout=20),
    SETTLE,
))

SKIP_SCENE = Task("skip-scene", "跳過劇情", (
    Click("menu.png", "清單", optional=True),
    Click("skip-scene.png", "跳過", optional=True),
    Click("dialog-skip.png", "對話跳過", optional=True),
))

CLICK_SKIP = Task("click-skip", "點擊跳過按鈕", (
    Click("skip-play.png", "跳過按鈕"),
))

GO_HOME = Task("home", "回到主頁", (
    HOME,
))

TASKS: dict[str, Task] = {
    task.name: task
    for task in (FREE_GACHAPON, EXPLORER, DUNGEON, SKIP_SCENE, CLICK_SKIP, GO_HOME)
}

DAILY_ROUTINE: tuple[str, ...] = ("free-gachapon", "explorer", "dungeon")
"""What ``python main.py`` runs when you name no task."""
