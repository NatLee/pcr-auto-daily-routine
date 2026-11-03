"""``python main.py [TASK ...]``: run the daily routine, or just the tasks you name."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence

from .bot import Bot
from .config import Settings
from .device import DesktopScreen, DeviceError, MousePointer, Pointer, Screen
from .routine import DAILY_ROUTINE, TASKS
from .vision import TemplateError, load_templates

log = logging.getLogger(__name__)


def desktop(settings: Settings) -> tuple[Screen, Pointer]:
    return DesktopScreen(settings.monitor), MousePointer()


def build_parser() -> argparse.ArgumentParser:
    width = max(map(len, TASKS))
    listing = "\n".join(f"  {name:<{width}}  {task.title}" for name, task in TASKS.items())
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Play the daily chores of Princess Connect! Re:Dive in an emulator window: "
            "it looks at the screen and clicks the buttons it finds."
        ),
        epilog=(
            f"tasks:\n{listing}\n\n"
            f"With no TASK it runs: {' '.join(DAILY_ROUTINE)}\n"
            "Exit status: 0 if every task finished, 1 if one stopped early or setup failed, "
            "2 for a bad command line."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("tasks", nargs="*", metavar="TASK", help="tasks to run, in this order")
    return parser


def main(argv: Sequence[str] | None = None, *, settings: Settings | None = None,
         devices: Callable[[Settings], tuple[Screen, Pointer]] = desktop) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    names = args.tasks or list(DAILY_ROUTINE)
    unknown = [name for name in names if name not in TASKS]
    if unknown:
        parser.error(f"unknown task {', '.join(unknown)} (choose from {', '.join(TASKS)})")
    tasks = [TASKS[name] for name in names]
    settings = settings or Settings()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    try:
        templates = load_templates(settings.image_dir, (i for task in tasks for i in task.images()))
        screen, pointer = devices(settings)
    except (TemplateError, DeviceError) as error:
        print(f"{parser.prog}: error: {error}", file=sys.stderr)
        return 1
    bot = Bot(screen, pointer, templates, settings)

    try:
        results = [(task.name, task.run(bot)) for task in tasks]
    except DeviceError as error:
        print(f"{parser.prog}: error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"{parser.prog}: stopped", file=sys.stderr)
        return 130

    for name, done in results:
        log.info("%s：%s", name, "完成" if done else "沒有完成")
    return 0 if all(done for _, done in results) else 1
