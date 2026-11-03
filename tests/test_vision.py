from __future__ import annotations

import shutil

import cv2
import numpy as np
import pytest
from fakes import SETTINGS, noise, template

from pcr_routine.vision import Match, TemplateError, find, load_template, load_templates, to_gray

THRESHOLD = SETTINGS.match_threshold
ALL_IMAGES = sorted(path.name for path in SETTINGS.image_dir.glob("*.png"))


def paste(screen: np.ndarray, image: np.ndarray, left: int, top: int) -> np.ndarray:
    screen = screen.copy()
    screen[top:top + image.shape[0], left:left + image.shape[1]] = image
    return screen


@pytest.mark.parametrize("name", ALL_IMAGES)
def test_load_template_gives_the_same_pixels_as_the_original_script(name):
    # The original read each button with cv2.imread and converted it with BGR2GRAY.
    original = cv2.cvtColor(cv2.imread(str(SETTINGS.image_dir / name)), cv2.COLOR_BGR2GRAY)
    assert np.array_equal(load_template(SETTINGS.image_dir / name), original)


def test_load_template_reads_paths_with_chinese_characters(tmp_path):
    folder = tmp_path / "公主連結"
    folder.mkdir()
    shutil.copy(SETTINGS.image_dir / "OK.png", folder / "OK.png")
    assert np.array_equal(load_template(folder / "OK.png"), template("OK.png"))


def test_missing_image_names_the_file(tmp_path):
    with pytest.raises(TemplateError, match=r"not found: .*nope\.png"):
        load_template(tmp_path / "nope.png")


def test_a_file_that_is_not_an_image_is_reported(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_text("not a picture")
    with pytest.raises(TemplateError, match="Not an image"):
        load_template(bad)


def test_load_templates_loads_each_name_once():
    loaded = load_templates(SETTINGS.image_dir, ["OK.png", "menu.png", "OK.png"])
    assert list(loaded) == ["OK.png", "menu.png"]


def test_to_gray_matches_the_original_screenshot_conversion():
    # mss hands out BGRA; the original converted it with BGR2GRAY, which ignores alpha.
    bgra = np.random.default_rng(1).integers(0, 256, (40, 60, 4), dtype=np.uint8)
    assert np.array_equal(to_gray(bgra), cv2.cvtColor(bgra[:, :, :3], cv2.COLOR_BGR2GRAY))
    gray = bgra[:, :, 0]
    assert to_gray(gray) is gray


# The first qualifying spot can sit a few pixels above or left of the perfect fit: up to 7 px
# for the mostly transparent go-mana image on this noise (measured with OpenCV 5.0).
NEAR = 8


@pytest.mark.parametrize("name", ALL_IMAGES)
def test_find_locates_every_button_where_it_was_pasted(name):
    button = template(name)
    height, width = button.shape
    screen = paste(noise(), button, left=301, top=97)
    match = find(screen, button, THRESHOLD)
    assert match is not None
    assert (match.width, match.height) == (width, height)
    assert 0 <= 301 - match.left < NEAR and 0 <= 97 - match.top < NEAR
    x, y = match.center
    assert 301 <= x < 301 + width and 97 <= y < 97 + height
    assert match.score >= THRESHOLD


def test_find_returns_none_when_the_button_is_not_there():
    assert find(noise(), template("OK.png"), THRESHOLD) is None


def test_find_returns_none_when_the_button_is_bigger_than_the_screen():
    assert find(noise(size=(50, 50)), template("OK.png"), THRESHOLD) is None


def test_find_prefers_the_higher_copy_of_a_button():
    button = template("OK.png")
    screen = paste(paste(noise(), button, 200, 300), button, 900, 80)
    match = find(screen, button, THRESHOLD)
    assert abs(match.left - 900) < NEAR and abs(match.top - 80) < NEAR


def test_find_reads_the_scores_row_by_row_from_the_top_left():
    # Two spots score exactly the threshold: the upper one wins even though it is further right.
    screen = np.zeros((40, 40), np.uint8)
    screen[5:8, 30:33] = 255
    screen[20:23, 2:5] = 255
    button = np.zeros((5, 5), np.uint8)
    button[1:4, 1:4] = 255
    match = find(screen, button, threshold=0.999)
    assert (match.left, match.top) == (29, 4)


def test_find_respects_the_threshold():
    button = template("OK.png")
    blurred = cv2.GaussianBlur(button, (0, 0), 3)
    screen = paste(noise(), blurred, 400, 200)
    score = cv2.matchTemplate(screen, button, cv2.TM_CCOEFF_NORMED).max()
    assert 0 < score < 1
    assert find(screen, button, float(score) - 0.01) is not None
    assert find(screen, button, float(score) + 0.01) is None


def test_center_rounds_down_like_the_original():
    # The original clicked ((x1 + x2) // 2, (y1 + y2) // 2) with x2 = x1 + width.
    assert Match(left=10, top=20, width=5, height=7, score=1.0).center == (12, 23)
    assert Match(left=-1915, top=-200, width=111, height=40, score=1.0).center == (-1860, -180)


def test_moved_keeps_the_size_and_score():
    match = Match(1, 2, 3, 4, 0.9).moved(-1920, 10)
    assert match == Match(-1919, 12, 3, 4, 0.9)
