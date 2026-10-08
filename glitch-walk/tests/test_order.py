"""The three kinds of step and how the build decides which one a step is.

    uv run --with pytest pytest tests

A number: it happens once, after the step before it has finished.
A number and a letter: it happens inside or alongside the step before it.
"Only if": it did not happen in this walk and is not counted.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import build  # noqa: E402


def step(name, start, end, marks, **more):
    return dict({"name": name, "title": f"{name} does a thing.", "why": "So it works.", "here": "It does it here.",
                 "icon": "list", "files": ["app"],
                 "code": [{"file": "app", "start": start, "end": end, "marks": marks, "plain": "These lines do it."}]}, **more)


@pytest.fixture
def walk(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.js").write_text("\n".join(f"line {i}" for i in range(1, 21)), encoding="utf-8")
    folder = tmp_path / "walk"
    folder.mkdir()

    def go(steps, say="You press Go."):
        folder.joinpath("walk.json").write_text(json.dumps({
            "question": "What happens when I press Go?", "shape": "A", "place": "the app", "root": "../project",
            "run": "Read from the code. Nothing was sent.",
            "about": {"what": "An app.", "who": "Anyone.", "on": "One button.", "address": "the app"},
            "files": [{"id": "app", "path": "app.js", "kind": "runs in your browser", "says": "The app."}],
            "moments": [{"state": "do", "say": say,
                         "screen": {"source": "Drawn: there is no screen to capture in a test.", "lines": [{"t": "out", "v": "Go"}]},
                         "hidden": steps}]}), encoding="utf-8")
        try:
            build.build(folder)
        except build.Refused as why:
            return str(why), None
        page = folder.joinpath("walk.html").read_text(encoding="utf-8")
        story = json.loads(page.split("window.STORY = ", 1)[1].split(";</script>", 1)[0].replace("<\\/", "</"))
        return capsys.readouterr().out, [h["label"] for h in story["moments"][0]["hidden"]]

    return go


def test_steps_in_sequence_are_numbered(walk):
    _, labels = walk([step("First", 1, 3, [2]), step("Second", 4, 6, [5]), step("Third", 7, 9, [8])])
    assert labels == ["1", "2", "3"]


def test_a_step_inside_another_takes_its_number_and_a_letter(walk):
    _, labels = walk([step("Loop", 1, 9, [1]), step("Turn", 2, 4, [3], inside=True), step("Draw", 5, 7, [6], inside=True),
                      step("Stop", 10, 12, [11])])
    assert labels == ["1", "1a", "1b", "2"]


def test_a_step_that_did_not_happen_has_no_number_and_is_not_counted(walk):
    out, labels = walk([step("First", 1, 3, [2]), step("Remove", 4, 6, [5], only_if="you press Yes"), step("Last", 7, 9, [8])])
    assert labels == ["1", "", "2"]
    assert "2 steps out of sight" in out


def test_a_step_that_lights_only_lines_already_lit_must_be_marked_inside(walk):
    why, _ = walk([step("Finish", 1, 9, [3, 5]), step("Log", 2, 4, [3])])
    assert "it lights only lines that step 1 already lights" in why and '"inside": true' in why


def test_the_same_step_marked_inside_is_accepted(walk):
    _, labels = walk([step("Finish", 1, 9, [3, 5]), step("Log", 2, 4, [3], inside=True)])
    assert labels == ["1", "1a"]


def test_nothing_can_be_inside_when_no_step_comes_before_it(walk):
    why, _ = walk([step("First", 1, 3, [2], inside=True)])
    assert "no numbered step comes before it" in why


def test_a_step_cannot_be_both_inside_and_only_if(walk):
    why, _ = walk([step("First", 1, 3, [2]), step("Odd", 4, 6, [5], inside=True, only_if="it rains")])
    assert "marked both" in why


# ---- the line for one thing you do or see

def test_a_line_of_a_hundred_characters_is_accepted(walk):
    out, labels = walk([step("First", 1, 3, [2])], say="You press Go. " + "x" * 86)
    assert labels == ["1"]


def test_a_longer_line_is_refused(walk):
    out, labels = walk([step("First", 1, 3, [2])], say="You press Go. " + "x" * 87)
    assert labels is None and "'say' is too long to sit on one line of the list" in out
