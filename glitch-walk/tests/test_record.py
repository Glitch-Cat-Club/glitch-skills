"""A screen with no web page: what a real run printed, read from a recording and never typed.

    uv run --with pytest pytest tests
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))
import build  # noqa: E402


def record(*args) -> None:
    subprocess.run([sys.executable, str(SRC / "record.py"), *map(str, args)], check=True, capture_output=True)


@pytest.fixture
def walk(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("\n".join(f"line {i}" for i in range(1, 21)), encoding="utf-8")
    folder = tmp_path / "walk"
    folder.mkdir()

    def go(screen):
        folder.joinpath("walk.json").write_text(json.dumps({
            "question": "What happens when I run it?", "shape": "A", "place": "your terminal", "root": "../project",
            "run": "Read from the code. Nothing was changed.",
            "about": {"what": "A script.", "who": "You.", "on": "No screen.", "address": "your terminal"},
            "files": [{"id": "app", "path": "app.py", "kind": "runs on your machine", "says": "The script."}],
            "moments": [{"state": "do", "say": "You run it.", "screen": screen,
                         "hidden": [{"name": "Run", "title": "Runs.", "why": "So it works.", "here": "It ran.", "icon": "list",
                                     "files": ["app"],
                                     "code": [{"file": "app", "start": 1, "end": 2, "marks": [1], "plain": "This line does it."}]}]}],
        }), encoding="utf-8")
        page = build.build(folder).read_text(encoding="utf-8")
        capsys.readouterr()
        story = page.split("window.STORY = ", 1)[1].split(";</script>", 1)[0]
        return json.loads(story.replace("<\\/", "</"))["moments"][0]["screen"]

    go.folder = folder
    return go


def test_a_command_is_shown_as_it_really_printed(walk):
    record(walk.folder / "shots" / "run.txt", "--", sys.executable, "-c", "print('one'); print('two'); print('three')")
    seen = walk({"output": "run", "start": 1, "end": 3, "marks": [2], "typed": "run it", "source": "Recorded today."})
    assert seen["real"] is True
    assert seen["lines"][0] == {"t": "prompt", "v": "run it"}
    assert seen["lines"][2]["t"] == "tool" and "print('one')" in seen["lines"][2]["v"]
    assert seen["lines"][3:] == [{"t": "dim", "v": "one"}, {"t": "", "v": "two"}, {"t": "dim", "v": "three"}]


def test_a_file_is_shown_as_it_really_stands(walk, tmp_path):
    log = tmp_path / "it.log"
    log.write_text("a | other\nb | mine\nc | other\nd | mine\n", encoding="utf-8")
    record(walk.folder / "shots" / "log.txt", "--file", log, "--match", "mine", "--last", "1")
    seen = walk({"output": "log", "start": 1, "end": 1, "source": "Recorded today."})
    assert seen["lines"] == [{"t": "dim", "v": "it.log"}, {"t": "", "v": "d | mine"}]


def test_a_long_line_is_cut_and_says_so(walk):
    record(walk.folder / "shots" / "run.txt", "--", sys.executable, "-c", "print('x' * 500)")
    seen = walk({"output": "run", "start": 1, "end": 1, "source": "Recorded today."})
    assert seen["lines"][-1]["v"] == "x" * build.WIDE + " ..."


def test_typed_lines_are_refused(walk):
    record(walk.folder / "shots" / "run.txt", "--", sys.executable, "-c", "print('one')")
    with pytest.raises(build.Refused, match="typed"):
        walk({"output": "run", "start": 1, "end": 1, "source": "Recorded today.", "lines": [{"t": "", "v": "made up"}]})


def test_a_recording_that_is_not_there_is_refused(walk):
    with pytest.raises(build.Refused, match="record.py"):
        walk({"output": "run", "start": 1, "end": 1, "source": "Recorded today."})
    (walk.folder / "shots").mkdir()
    (walk.folder / "shots" / "run.txt").write_text("typed by hand\n", encoding="utf-8")
    with pytest.raises(build.Refused, match="record.py"):
        walk({"output": "run", "start": 1, "end": 1, "source": "Recorded today."})


def test_lines_that_are_not_in_the_recording_are_refused(walk):
    record(walk.folder / "shots" / "run.txt", "--", sys.executable, "-c", "print('one')")
    with pytest.raises(build.Refused, match="not in"):
        walk({"output": "run", "start": 1, "end": 4, "source": "Recorded today."})


def test_a_screen_can_show_only_what_was_typed(walk):
    seen = walk({"typed": "/go", "source": "Only what you type is shown: it was not run."})
    assert seen["lines"] == [{"t": "prompt", "v": "/go"}] and "real" not in seen


def test_drawn_lines_that_would_show_as_blanks_are_refused(walk):
    for lines in ([], ["/go"]):
        with pytest.raises(build.Refused, match="typed"):
            walk({"typed": "/go", "lines": lines, "source": "Drawn."})


def test_something_they_see_cannot_be_a_screen_of_typed_words(walk, tmp_path):
    w = json.loads((walk.folder / "walk.json").read_text(encoding="utf-8")) if (walk.folder / "walk.json").exists() else None
    walk({"typed": "/go", "source": "Only what you type is shown: it was not run."})
    w = json.loads((walk.folder / "walk.json").read_text(encoding="utf-8"))
    for state in ("see", "wait"):
        w["moments"][0]["state"] = state
        (walk.folder / "walk.json").write_text(json.dumps(w), encoding="utf-8")
        with pytest.raises(build.Refused, match="nothing was seen"):
            build.build(walk.folder)
