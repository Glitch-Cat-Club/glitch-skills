"""The start of a walk, one test per case.

    uv run --with pytest pytest tests

Each test fills in start.json as the model would and reads what the check tells it to say.
The project it looks at is made here from nothing, so no test depends on any one real site.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import start  # noqa: E402

RANT = ("I vibe-coded this for nine months and I'm so lost. When I do things it breaks. "
        "I don't understand GitHub. I don't like the design. I've got three databases.")
LIST = ["Asking for a gift idea", "Saving an idea", "Signing in", "Sharing a list"]
ONE = {"projects": [{"name": "Your gift app", "path": "../project", "says": "It suggests gifts."}], "fits": True}
TWO = [{"name": "Your gift app", "path": "../project", "says": "It suggests gifts."},
       {"name": "The client dashboard", "path": "../project", "says": "Charts for a client."}]
SORTED = {"asked": RANT, "shape": "C", "lost": True}


@pytest.fixture
def run(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.js").write_text("// the app\n", encoding="utf-8")
    walk = tmp_path / "walk"
    walk.mkdir()

    def go(s: dict):
        (walk / "start.json").write_text(json.dumps(s), encoding="utf-8")
        code = start.check(walk)
        return code, capsys.readouterr().out

    go.walk = walk
    go.project = project
    return go


def looked(kind="an app with screens", all_of_it=True, read=("app.js",)):
    return {"thing": "your gift app", "kind": kind, "all": all_of_it,
            "parts": [{"name": "The app", "says": "Suggests gifts."}], "read": list(read)}


def listed(lost=True, shape="C", **look):
    return {"asked": RANT, "shape": shape, "lost": lost, "where": ONE, "look": looked(**look),
            "narrow": {"list": LIST, "first": 1}}


def ready(shape="C", link="Asking for an idea is the main thing your app does.", start_="You ask for a gift idea."):
    s = listed(shape=shape)
    s["narrow"].update(said="1", picked=1)
    if shape == "A":
        del s["narrow"]
    s["action"] = {"question": "What happens when I ask for a gift idea?", "start": start_, "link": link,
                   "end": "A list of ideas appears.", "files": ["app.js"],
                   "seen": {"kind": "page", "where": "the Ideas screen"}, "needs": ""}
    s["confirmed"] = "yes"
    return s


# ---- how they arrive

def test_started_with_nothing_asks_the_one_opening_question(run, capsys):
    code = start.check(run.walk)
    out = capsys.readouterr().out
    assert code == 2
    assert "A walk shows you how one part of your project works.\nWhat do you want to understand?" in out


def test_what_they_asked_is_sorted_before_anything_is_read(run):
    code, out = run({"asked": RANT})
    assert code == 2 and "NEXT: step 2, shape." in out


def test_a_fix_or_advice_is_caught_at_once_with_two_plain_choices(run):
    code, out = run({"asked": "Can you fix my login?", "shape": "none", "lost": False})
    assert code == 2
    assert ("A walk only shows you what is already in your project. It doesn't change it or give advice.\n"
            "Stop the walk and do that, or carry on with the walk?") in out
    assert "Do not ask them anything else" in out


def test_they_can_stop_the_walk_at_any_step(run):
    s = listed()
    s["stopped"] = True
    code, out = run(s)
    assert code == 3 and out.startswith("STOPPED.")


# ---- which project

def test_one_project_in_the_folder_is_found_without_asking(run):
    code, out = run(dict(SORTED, where=ONE))
    assert code == 2 and "3 where    done" in out and "NEXT: step 4, look." in out


def test_several_projects_and_their_words_point_at_one(run):
    code, out = run(dict(SORTED, where={"projects": TWO, "guess": 2}))
    assert code == 2 and "SAY, word for word:\n\nDo you mean The client dashboard?" in out


def test_several_projects_and_none_stands_out(run):
    code, out = run(dict(SORTED, where={"projects": TWO, "guess": 0}))
    assert ("I can see more than one project here:\n\n1. Your gift app\n2. The client dashboard\n\n"
            "Which one do you mean? Give me the number, or tell me where it is.") in out


def test_thirty_projects_are_never_all_listed(run):
    many = [{"name": f"Project {i}", "path": "../project", "says": f"It does thing {i}."} for i in range(1, 31)]
    code, out = run(dict(SORTED, where={"projects": many, "guess": 0}))
    assert code == 1 and "do not list them all" in out
    code, out = run(dict(SORTED, where={"projects": many, "guess": 0, "closest": [4, 17]}))
    assert code == 2
    assert ("I can see 30 projects here and none of them sounds quite like what you described. The closest are:\n\n"
            "1. Project 4: It does thing 4.\n2. Project 17: It does thing 17.\n\n"
            "Is it one of these? Give me the number, or tell me its name or where it is.") in out
    assert "Project 9" not in out and "1 is project 4, 2 is project 17" in out


def test_what_it_found_does_not_sound_like_what_they_described(run):
    code, out = run(dict(SORTED, where=dict(ONE, fits=False)))
    assert code == 2
    assert ("What I can see here is Your gift app: It suggests gifts.\n"
            "That doesn't sound like what you described. Is this the one, or is it somewhere else?") in out


def test_it_must_say_whether_what_it_found_fits(run):
    code, out = run(dict(SORTED, where={"projects": ONE["projects"]}))
    assert code == 1 and "'fits' must be true or false" in out


def test_a_project_folder_that_is_not_there_is_refused(run):
    code, out = run(dict(SORTED, where={"projects": [{"name": "X", "path": "../nowhere", "says": "x"}]}))
    assert code == 1 and "does not point at a folder" in out


# ---- the look

def test_it_cannot_skip_the_look(run):
    code, out = run(dict(SORTED, where=ONE, narrow={"list": LIST, "first": 1}))
    assert code == 2 and "NEXT: step 4, look." in out


def test_a_file_it_never_opened_is_refused(run):
    code, out = run(dict(SORTED, where=ONE, look=looked(read=("app.js", "made-up.js"))))
    assert code == 1 and "made-up.js is not in" in out


def test_a_small_project_is_never_called_big(run):
    code, out = run(listed(all_of_it=False))
    assert code == 1 and "few enough to read" in out


def test_pictures_and_notes_do_not_make_a_project_big(run):
    for i in range(200):
        (run.project / f"photo{i}.png").write_bytes(b"x")
        (run.project / f"note{i}.md").write_text("x", encoding="utf-8")
    code, out = run(listed(all_of_it=False))
    assert code == 1 and "this project has 1 code file," in out


# ---- the list

def test_a_wild_rant_gets_the_list_whatever_it_said(run):
    code, out = run(listed())
    assert code == 2
    assert ("Let's slow it down. I've looked through your project.\n\n"
            "Let's take one part at a time. Here's what I can see people doing with your gift app:\n\n"
            "1. Asking for a gift idea\n2. Saving an idea\n3. Signing in\n4. Sharing a list\n\n"
            "Which one do you want to see working? Give me the number, or tell me something else.\n"
            "Not sure? I'd start with 1.") in out


def test_someone_who_is_not_lost_is_not_told_to_slow_down(run):
    _, out = run(listed(lost=False))
    assert "slow it down" not in out
    assert "SAY, word for word:\n\nLet's take one part at a time." in out


def test_a_big_project_says_it_has_not_read_it_all(run):
    for i in range(start.SMALL):
        (run.project / f"file{i}.js").write_text("//\n", encoding="utf-8")
    _, out = run(listed(all_of_it=False))
    assert ("Let's slow it down. This is a big project, so I haven't read all of it. "
            "These are the main things I found.\n\nLet's take one part at a time.") in out
    assert "I've looked through your project" not in out


def test_the_list_is_as_long_as_the_project(run):
    s = listed()
    s["narrow"]["list"] = [f"Doing thing {i}" for i in range(1, 12)]
    _, out = run(s)
    assert "11. Doing thing 11" in out


def test_a_list_always_comes_with_somewhere_to_start(run):
    s = listed()
    del s["narrow"]["first"]
    code, out = run(s)
    assert code == 1 and "the one you would start with" in out


@pytest.mark.parametrize("kind,who", [("a website", "people"), ("a skill", "you"), ("an automation", "you")])
def test_who_does_it_follows_the_kind_of_project(run, kind, who):
    _, out = run(listed(kind=kind))
    assert f"Here's what I can see {who} doing with your gift app:" in out


def test_what_changed_is_introduced_as_what_changed(run):
    _, out = run(listed(shape="G", lost=False))
    assert "Here's what works differently in your gift app since the last change:" in out


def test_a_part_is_introduced_as_that_part(run):
    _, out = run(listed(shape="B", lost=False))
    assert "Here's what I can see people doing with that part of your gift app:" in out


def test_something_else_sends_it_back_to_look(run):
    s = listed()
    s["narrow"].update(said="the bit that talks to the AI", picked=0)
    code, out = run(s)
    assert code == 2 and "they named something else" in out


def test_a_pick_that_is_not_on_the_list_is_refused(run):
    s = listed()
    s["narrow"].update(said="nine", picked=9)
    code, out = run(s)
    assert code == 1 and "REFUSED" in out


# ---- the one thing and the yes

def test_a_question_that_is_not_a_walk_is_refused(run):
    s = ready()
    s["action"]["question"] = "How does my app work?"
    code, out = run(s)
    assert code == 1 and "Every walk is of one thing someone does" in out


def test_it_says_how_this_answers_what_they_asked(run):
    s = ready(shape="F", link="There is one API in your app: the part that fetches the ideas.")
    del s["confirmed"], s["narrow"]
    s["narrow"] = {"found": "You ask for a gift idea."}
    code, out = run(s)
    assert code == 2
    assert ("There is one API in your app: the part that fetches the ideas.\n"
            "I'll show you what happens when you ask for a gift idea.\n"
            "Nothing will be sent or changed for real.\nOK?") in out


def test_it_cannot_skip_saying_how_this_answers_them(run):
    code, out = run(ready(link=""))
    assert code == 1 and "'link' cannot be empty" in out


def test_asked_for_exactly_this_needs_no_link(run):
    s = ready(shape="A", link="")
    del s["confirmed"]
    code, out = run(s)
    assert code == 2
    assert "SAY, word for word:\n\nI'll show you what happens when you ask for a gift idea.\n" in out


def test_a_visitor_can_be_the_one_who_does_it(run):
    s = ready(start_="A visitor fills in the form and presses Send.")
    del s["confirmed"]
    _, out = run(s)
    assert "I'll show you what happens when a visitor fills in the form and presses Send.\n" in out


def test_nothing_is_walked_until_they_say_yes(run):
    s = ready()
    del s["confirmed"]
    code, out = run(s)
    assert code == 2 and "Nothing will be sent or changed for real.\nOK?" in out


def test_a_full_start_is_ready(run):
    code, out = run(ready())
    assert code == 0 and "READY. Walk it." in out


def test_a_thing_with_no_web_page_is_walked_too(run):
    for kind in ("terminal", "left"):
        s = ready()
        s["action"]["seen"]["kind"] = kind
        code, out = run(s)
        assert code == 0 and "READY. Walk it." in out


def test_a_question_about_what_they_do_is_asked_as_they_would_ask_it(run):
    s = ready()
    s["action"]["question"] = "What happens when you ask for a gift idea?"
    code, out = run(s)
    assert code == 1 and "What happens when I" in out
