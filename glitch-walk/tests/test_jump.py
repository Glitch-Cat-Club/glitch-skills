"""Jump to, under every mix of how many things a walk has, how long their lines are and how wide the screen is.

    uv run --with pytest --with playwright pytest tests

Up to four things sit in one row with their words, when every word fits.
Otherwise the row holds the numbers and the full list sits underneath.
Whichever it is, no line is ever cut, nothing runs off the screen and pressing a line goes to it.
Needs Chrome. Without playwright these tests are skipped.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import build  # noqa: E402

sync_api = pytest.importorskip("playwright.sync_api")

THINGS = (2, 3, 4, 5, 6, 9, 14, 25)
SCREENS = {"desktop": 1400, "laptop": 1100, "tablet": 820, "phone": 390}
SHORT = "You press Spin."
MIDDLING = "The wheel stops, a name appears under it and confetti falls."
LONGEST = "The wheel slows down over four seconds and stops with the pointer resting on one name in the roster."
LINES = {"short": [SHORT], "middling": [MIDDLING], "longest": [LONGEST], "mixed": [SHORT, LONGEST, MIDDLING]}

MEASURE = """() => {
  const cut = (n) => n.scrollWidth > n.clientWidth + 1;
  const bar = document.querySelector('.strip'), box = bar.getBoundingClientRect();
  const cells = [...bar.querySelectorAll('.cells button')], list = [...document.querySelectorAll('.contents li b')];
  return {
    sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    list: bar.classList.contains('many'),
    cells: cells.length,
    outside: cells.filter((c) => { const r = c.getBoundingClientRect(); return r.left < box.left - 1 || r.right > box.right + 1 || r.bottom > box.bottom + 1; }).length,
    row: cells.map((c) => c.querySelector('b')).filter(Boolean).map((b) => [b.textContent, cut(b)]),
    lines: list.map((b) => [b.textContent, cut(b)]),
  };
}"""

# the page glides to where it is going, so wait until it has stopped moving
STILL = """() => new Promise((done) => { let last = -1, same = 0;
  const tick = () => { same = scrollY === last ? same + 1 : 0; last = scrollY; same > 8 ? done() : requestAnimationFrame(tick); };
  setTimeout(tick, 100); })"""


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        chrome = p.chromium.launch(channel="chrome", headless=True)
        yield chrome
        chrome.close()


def numbered(line: str, n: int) -> str:
    """The line with its number on the end, so every line of a walk is different, kept within the longest allowed."""
    end = f" {n}."
    return line[:-1][:build.SAY - len(end)] + end


def a_walk(folder: Path, says: list) -> Path:
    """Build a real page with one thing you do or see for each line in says."""
    project = folder / "project"
    project.mkdir()
    (project / "app.js").write_text("\n".join(f"line {i}" for i in range(1, 400)), encoding="utf-8")
    walk = folder / "walk"
    walk.mkdir()
    moments = [{"state": "do", "say": say,
                "screen": {"source": "Drawn: there is no screen to capture in a test.", "lines": [{"t": "out", "v": "Go"}]},
                "hidden": [{"name": f"Step {i}", "title": "Does a thing.", "why": "So it works.", "here": "It does it here.",
                            "icon": "list", "files": ["app"],
                            "code": [{"file": "app", "start": i * 3, "end": i * 3 + 1, "marks": [i * 3], "plain": "This line does it."}]}]}
               for i, say in enumerate(says, 1)]
    walk.joinpath("walk.json").write_text(json.dumps({
        "question": "What happens when I press Spin?", "shape": "A", "place": "the app", "root": "../project",
        "run": "Read from the code. Nothing was sent.",
        "about": {"what": "An app.", "who": "Anyone.", "on": "One button.", "address": "the app"},
        "files": [{"id": "app", "path": "app.js", "kind": "runs in your browser", "says": "The app."}],
        "moments": moments}), encoding="utf-8")
    return build.build(walk)


@pytest.mark.parametrize("length", LINES)
@pytest.mark.parametrize("things", THINGS)
def test_no_line_is_ever_cut(browser, tmp_path, things, length):
    says = [numbered(LINES[length][i % len(LINES[length])], i + 1) for i in range(things)]
    page_file = a_walk(tmp_path, says)
    page = browser.new_page()
    try:
        for screen, width in SCREENS.items():
            where = f"{things} things, {length} lines, {screen}"
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(page_file.as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(250)
            seen = page.evaluate(MEASURE)

            assert not seen["sideways"], f"{where}: the page scrolls sideways"
            assert seen["cells"] == things, f"{where}: {seen['cells']} numbers in the bar"
            assert seen["outside"] == 0, f"{where}: a number sits outside the bar"
            if things > 4:
                assert seen["list"], f"{where}: more than four things and no list"
            shown = seen["lines"] if seen["list"] else seen["row"]
            assert [text for text, _ in shown] == says, f"{where}: the lines shown are not the lines of the walk"
            assert not [text for text, cut in shown if cut], f"{where}: a line is cut"

            # pressing the last line brings the last thing onto the screen
            target = ".contents li:last-child button" if seen["list"] else ".strip .cells button:last-child"
            page.locator(target).click()
            page.evaluate(STILL)
            top = page.evaluate(f"document.getElementById('m{things - 1}').getBoundingClientRect().top")
            assert -5 <= top < 900, f"{where}: pressing the last line did not go to it"
    finally:
        page.close()


def test_the_row_comes_back_when_the_window_is_wide_enough(browser, tmp_path):
    page_file = a_walk(tmp_path, ["You press Spin.", "The wheel spins.", "The wheel stops on a name.", "A pop-up asks about the winner."])
    page = browser.new_page()
    try:
        page.set_viewport_size({"width": 1400, "height": 900})
        page.goto(page_file.as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert not page.evaluate(MEASURE)["list"]
        page.set_viewport_size({"width": 820, "height": 900})
        page.wait_for_timeout(500)
        assert page.evaluate(MEASURE)["list"]
        page.set_viewport_size({"width": 1400, "height": 900})
        page.wait_for_timeout(500)
        assert not page.evaluate(MEASURE)["list"]
    finally:
        page.close()
