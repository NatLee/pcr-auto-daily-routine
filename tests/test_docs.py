"""The README pictures are drawn from docs/images/src/routine.js; it must match the code."""

from __future__ import annotations

import importlib.util

from pcr_routine.config import REPO_ROOT

EXPORTER = REPO_ROOT / "docs" / "images" / "src" / "export_routine.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_routine", EXPORTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_routine_js_is_up_to_date():
    exporter = load_exporter()
    expected = exporter.render(exporter.build())
    actual = exporter.OUTPUT.read_text(encoding="utf-8")
    assert actual == expected, "run: python docs/images/src/export_routine.py, then re-render the pictures"


def test_visible_box_skips_the_transparent_margin():
    exporter = load_exporter()
    # adventure-explorer-exp-go-mana.png is a 492x125 canvas with the button in its top-left corner.
    x, y, w, h = exporter.visible_box(REPO_ROOT / "img" / "adventure-explorer-exp-go-mana.png")
    assert (x, y) == (0, 0) and w < 200 and h < 50
    assert exporter.visible_box(REPO_ROOT / "img" / "OK.png") == [0, 0, 111, 40]
