"""The start of a walk.

    uv run python src/start.py <walk folder>

People arrive with anything: one clear question, or a long muddle about a whole project.
Before a walk can begin, that has to become one thing someone does, in one project.

This file makes that happen the same way every time. The model keeps what it has learned in
<walk folder>/start.json and runs this after every change. It prints the seven steps, says
what to do next and refuses a step that was skipped or filled in wrongly.

Everything the person is told during the start is written here, word for word, so two people
who ask the same thing hear the same thing. Nothing is walked until this prints READY.
"""
import json
import os
import sys
from pathlib import Path

from build import SHAPES, Refused, need

# ---------------------------------------------------------------- what the person is told

OPENING = ("A walk shows you how one part of your project works.\n"
           "What do you want to understand?")

NOT_A_WALK = ("A walk only shows you what is already in your project. It doesn't change it or give advice.\n"
              "Stop the walk and do that, or carry on with the walk?")

SLOW_DOWN = "Let's slow it down. "
LOOKED = "I've looked through your project."
BIG_PROJECT = "This is a big project, so I haven't read all of it. These are the main things I found."

# How a list is introduced depends on what they asked: a part, the whole thing, or what changed.
INTRO = {"B": "Here's what I can see {who} doing with that part of {thing}:",
         "C": "Here's what I can see {who} doing with {thing}:",
         "G": "Here's what works differently in {thing} since the last change:"}

WHY_QUESTIONS = ("To show you why, I need three things:\n\n"
                 "1. What did you do?\n"
                 "2. What did you expect to happen?\n"
                 "3. What did you see instead? The exact words on the screen, if there were any.")

SAFE = "Nothing will be sent or changed for real."

# ---------------------------------------------------------------- the rules

KINDS = ("a website", "an app with screens", "a service people sign in to", "a database",
         "reports and data", "an automation", "a skill", "something else")
USED_BY_OTHERS = KINDS[:3]          # for these the list says "people"; for the rest it says "you"
SEEN = {"page": "a web page", "terminal": "a terminal", "left": "what it leaves behind"}
WHO = ("You ", "A ", "An ", "Someone ")
QUESTION = "What happens when"

SMALL = 40      # a project with this many code files or fewer is read in full and never called big
FEW = 5         # more projects than this are never all listed to the person
LINK = 160      # the longest the line tying the walk to their question may be

CODE = (".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".py", ".rb", ".php",
        ".go", ".java", ".cs", ".swift", ".kt", ".rs", ".sql", ".sh", ".ps1")
NOT_THEIRS = ("node_modules", "dist", "build", "__pycache__")

READY, REFUSED, NEXT, STOPPED = 0, 1, 2, 3


class Next(Exception):
    """This step is not finished. The message is what the model should do or say now."""


def say(words: str, then: str) -> Next:
    return Next(f"SAY, word for word:\n\n{words}\n\nTHEN {then}")


def numbered(lines) -> str:
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


def opened(project: Path, files, step: str) -> None:
    """Every file the model names has to be there. It cannot describe what it never opened."""
    if not files:
        raise Refused(f"{step}: it names no files. Name at least one you read.")
    for f in files:
        if not (project / f).is_file():
            raise Refused(f"{step}: {f} is not in {project}. Only name a file you opened.")


def code_files(project: Path) -> int:
    """How much code a project holds. Pictures, fonts, notes and built copies do not make it big."""
    count = 0
    for _, folders, files in os.walk(project):
        folders[:] = [f for f in folders if not f.startswith(".") and f not in NOT_THEIRS]
        count += sum(1 for f in files if f.lower().endswith(CODE))
    return count


def project_of(s: dict, folder: Path) -> Path:
    where = s["where"]
    return (folder / where["projects"][where.get("picked", 1) - 1]["path"]).resolve()


# ---------------------------------------------------------------- the seven steps

def asked(s: dict, folder: Path) -> str:
    """1. What they want, in their own words."""
    if not str(s.get("asked", "")).strip():
        raise say(OPENING,
                  'write "asked": their answer, word for word, however long.\n'
                  "If they already said what they want when they started, write that and say nothing.")
    words = s["asked"].split()
    return " ".join(words[:8]) + (" ..." if len(words) > 8 else "")


def shape(s: dict, folder: Path) -> str:
    """2. Which of the seven shapes they asked. Sorted before anything is read, so a request
    a walk cannot serve is caught at once."""
    if "shape" not in s:
        table = "\n".join(f"  {letter}  {words}" for letter, words in SHAPES.items())
        raise Next(f'DO: decide which shape "asked" is. Say nothing.\n{table}\n'
                   'WRITE "shape": the letter,\n'
                   'or "none" if they want something changed, fixed, tested or judged, want advice on what to choose,\n'
                   "or ask a general question that is not about what their own project does;\n"
                   'and "lost": true if they sound confused or overwhelmed, false if they asked one clear thing.')
    if s["shape"] == "none":
        raise say(NOT_A_WALK,
                  'if they want to stop, write "stopped": true.\n'
                  'If they want to carry on and say what they want to see, write that as "asked", '
                  'take "shape" out and sort it again.\n'
                  'If they only say carry on, set "shape" to "C" and "lost" to true. Do not ask them anything else.')
    if s["shape"] not in SHAPES:
        raise Refused(f"shape: must be one of {', '.join(SHAPES)}, or none.")
    if not isinstance(s.get("lost"), bool):
        raise Refused("shape: 'lost' must be true or false. True if they sound confused or overwhelmed.")
    return f"{s['shape']}: {SHAPES[s['shape']]}" + (" and they sound lost" if s["lost"] else "")


def where(s: dict, folder: Path) -> str:
    """3. Which project they mean. Nobody points the skill at one. It looks at what is there,
    and asks only when it has to."""
    w = s.get("where")
    if not w:
        raise Next("DO: find their project. Start in the folder they started you in and look around it. Say nothing yet.\n"
                   "A project is one thing someone built. It may be this folder, or one of several inside it.\n"
                   'WRITE "where": {"projects": [{"name": as they would say it, "path": the path from this walk folder,\n'
                   '    "says": what it is, in a few plain words}], every project you can see,\n'
                   '  "guess": if there are several, the number of the one their words point to, or 0 if none stands out,\n'
                   '  "fits": true if that one is what they described, false if nothing here sounds like it}')
    projects = w.get("projects", [])
    if not projects:
        raise Refused("where: it names no projects. Name every one you can see.")
    for p in projects:
        need(p, ("name", "path", "says"), "where, a project")
        if not (folder / p["path"]).resolve().is_dir():
            raise Refused(f"where: '{p['path']}' does not point at a folder.")

    if len(projects) > 1 and "picked" not in w:
        raise which_project(projects, w)
    if w.get("picked", 1) not in range(1, len(projects) + 1):
        raise Refused(f"where: 'picked' must be a number from 1 to {len(projects)}.")

    # Having found one, check it is the one they were talking about.
    mine = projects[w.get("picked", 1) - 1]
    if not isinstance(w.get("fits"), bool):
        raise Refused("where: 'fits' must be true or false. True if what you found is what they described, "
                      "false if it does not sound like it. Be honest: a wrong project wastes their time.")
    if not w["fits"] and not str(w.get("sure", "")).strip():
        raise say(f"What I can see here is {mine['name']}: {mine['says']}\n"
                  "That doesn't sound like what you described. Is this the one, or is it somewhere else?",
                  'write inside "where": "sure": their reply, word for word, if this is the one.\n'
                  'If it is somewhere else, find it, add it to "projects", pick it and set "fits" again.')
    return mine["name"] + (f", one of {len(projects)} here" if len(projects) > 1 else "")


def which_project(projects: list, w: dict) -> Exception:
    """Several projects in the folder. Say back the likely one, or offer a few. Never a wall of names."""
    guess = w.get("guess")
    if guess not in range(len(projects) + 1):
        return Refused(f"where: 'guess' must be a number from 1 to {len(projects)}, or 0 if none stands out.")
    if guess:
        return say(f"Do you mean {projects[guess - 1]['name']}?",
                   'write inside "where": "said": their reply, word for word and "picked": that number if they said yes.\n'
                   'If they said no, set "guess" to 0 and run this again.')
    elsewhere = 'If it is somewhere else, find it, add it to "projects" and pick it.'
    if len(projects) <= FEW:
        return say(f"I can see more than one project here:\n\n{numbered(p['name'] for p in projects)}\n\n"
                   "Which one do you mean? Give me the number, or tell me where it is.",
                   f'write inside "where": "said": their reply, word for word and "picked": the number.\n{elsewhere}')
    closest = w.get("closest", [])
    if not 1 <= len(closest) <= 3 or any(c not in range(1, len(projects) + 1) for c in closest):
        return Refused(f"where: with {len(projects)} projects and none standing out, do not list them all. "
                       'Add "closest": the numbers of the one to three that come nearest to what they described.')
    shown = numbered(f"{projects[c - 1]['name']}: {projects[c - 1]['says']}" for c in closest)
    key = ", ".join(f"{i} is project {c}" for i, c in enumerate(closest, 1))
    return say(f"I can see {len(projects)} projects here and none of them sounds quite like what you described. "
               f"The closest are:\n\n{shown}\n\n"
               "Is it one of these? Give me the number, or tell me its name or where it is.",
               f'write inside "where": "said": their reply, word for word, '
               f'and "picked": the project\'s own number ({key}).\n{elsewhere}')


def look(s: dict, folder: Path) -> str:
    """4. A look through the project: what it is, its parts and every file that was opened."""
    k = s.get("look")
    if not k:
        raise Next("DO: look through their project before you say anything else. Open the files; never answer from memory.\n"
                   'WRITE "look": {"thing": its name as it reads in a sentence, such as "your booking site",\n'
                   f'  "kind": one of {", ".join(KINDS)},\n'
                   '  "parts": [{"name": ..., "says": one line on what it is}], as many as it has,\n'
                   '  "read": [every file you opened, as a path inside their project],\n'
                   '  "all": true if you read every code file that matters, false only if there is too much code to read.\n'
                   "         Pictures, fonts, notes and built copies never count}")
    need(k, ("thing", "kind"), "look")
    if k["kind"] not in KINDS:
        raise Refused(f"look: 'kind' must be one of: {', '.join(KINDS)}.")
    parts = k.get("parts", [])
    if not parts:
        raise Refused("look: it names no parts. Name every part you can see, at a high level.")
    for p in parts:
        need(p, ("name", "says"), "look, a part")
    project = project_of(s, folder)
    opened(project, k.get("read"), "look")
    if not isinstance(k.get("all"), bool):
        raise Refused("look: 'all' must be true or false. False if the project is too big to have read every part.")
    count = code_files(project)
    if not k["all"] and count <= SMALL:
        raise Refused(f"look: this project has {count} code file{'' if count == 1 else 's'}, "
                      "which is few enough to read. Read all of it and set 'all' to true.")
    return (f"{k['thing']} ({k['kind']}), {len(parts)} parts, {len(k['read'])} files read"
            + ("" if k["all"] else ", not all of it"))


def narrow(s: dict, folder: Path) -> str:
    """5. One set move for each shape. Every move ends at one thing that can be walked."""
    asked_as, n = s["shape"], s.get("narrow", {})

    if asked_as == "A":             # they named the thing themselves
        return "nothing to narrow"

    if asked_as == "D":             # something went wrong: find out what they did and saw
        if not all(str(n.get(f, "")).strip() for f in ("did", "expected", "saw")):
            raise say(WHY_QUESTIONS,
                      'write "narrow": {"did": ..., "expected": ..., "saw": ...}, each in their words.\n'
                      "Ask again for any one they left out.")
        return "what they did, expected and saw"

    if asked_as in ("E", "F"):      # something on their screen, or an idea: find the action behind it
        behind = {"E": "the action that puts that on their screen", "F": "one thing they do that uses the idea"}
        if not str(n.get("found", "")).strip():
            raise Next(f"DO: find {behind[asked_as]}. Say nothing yet.\n"
                       'WRITE "narrow": {"found": that action, in one sentence}\n'
                       'If nothing in their project does, set "shape" to "none".')
        return "the action behind it, found"

    return pick_from_a_list(s, n)   # a part, the whole thing, or what changed


def pick_from_a_list(s: dict, n: dict) -> str:
    """Offer what can be walked as a numbered list, with somewhere to start for anyone who cannot choose."""
    asked_as, seen_so_far = s["shape"], s["look"]
    listing = {"B": "someone doing that passes through that part",
               "C": "someone doing with it",
               "G": "someone doing that now behaves differently"}
    items = n.get("list", [])
    if not items:
        raise Next(f"DO: list what you can see {listing[asked_as]}, from the files in look.read. Say nothing yet.\n"
                   "Every line is one thing someone does that you could walk, in a few plain words\n"
                   '(for example "Sending the request form").\n'
                   'WRITE "narrow": {"list": [every one you can see; if look.all is false, the four that matter most],\n'
                   '  "first": the number of the one you would start with, the one that shows them most}')
    if any(not str(item).strip() for item in items):
        raise Refused("narrow: a line in the list is empty.")
    if n.get("first") not in range(1, len(items) + 1):
        raise Refused(f"narrow: 'first' must be a number from 1 to {len(items)}: the one you would start with.")

    if "picked" not in n:
        who = "people" if seen_so_far["kind"] in USED_BY_OTHERS else "you"
        opener = SLOW_DOWN if s["lost"] else ""
        if not seen_so_far["all"]:
            opener += BIG_PROJECT
        elif s["lost"]:
            opener += LOOKED
        raise say(f"{opener + chr(10) * 2 if opener else ''}"
                  f"Let's take one part at a time. {INTRO[asked_as].format(who=who, thing=seen_so_far['thing'])}\n\n"
                  f"{numbered(items)}\n\n"
                  "Which one do you want to see working? Give me the number, or tell me something else.\n"
                  f"Not sure? I'd start with {n['first']}.",
                  'write inside "narrow": "said": their reply, word for word,\n'
                  'and "picked": the number they chose, or 0 if they named something else.\n'
                  'If they cannot choose or leave it to you, "picked" is the one you said you would start with.')
    if n["picked"] == 0:
        raise Next("DO: they named something else. Look in their project for what they said, "
                   "and add any file you open to look.read.\n"
                   'WRITE "narrow": {"list": [what you can see someone doing there], "first": ...}, '
                   'with "said" and "picked" taken out.')
    if n["picked"] not in range(1, len(items) + 1):
        raise Refused(f"narrow: 'picked' must be a number from 1 to {len(items)}, or 0 for something else.")
    return f"they picked {n['picked']}: {items[n['picked'] - 1]}"


def action(s: dict, folder: Path) -> str:
    """6. The one thing that will be walked, who does it and how it answers what they asked."""
    a = s.get("action")
    if not a:
        raise Next("DO: pin down the one thing you will walk. Say nothing yet.\n"
                   f'WRITE "action": {{"question": the one question you will walk, starting "{QUESTION}",\n'
                   '  "start": who does what, in one sentence: "You press ...", or "A visitor fills in ..." when it is not them,\n'
                   '  "end": what is seen at the end,\n'
                   '  "link": one short sentence tying this to what they asked, in their own words where you can,\n'
                   '          such as "There is one API in your site: the part that receives the form.";\n'
                   '          "" only if they asked for exactly this action,\n'
                   '  "files": [the files this action passes through, as paths inside their project],\n'
                   f'  "seen": {{"kind": one of {", ".join(SEEN)}, "where": the address or place they would recognise}}}}')
    need(a, ("question", "start", "end"), "action")
    if not a["question"].startswith(QUESTION):
        raise Refused(f'action: \'question\' must start "{QUESTION}". Every walk is of one thing someone does.')
    if a["start"].startswith("You ") and " I " not in f" {a['question']} ":
        raise Refused('action: they do this themselves, so the question is theirs. Write it as they would ask it: '
                      f'"{QUESTION} I ...".')
    if not a["start"].startswith(WHO):
        raise Refused('action: \'start\' says who does it, so it starts "You ", "A visitor ", "A member " or "Someone ".')
    if "link" not in a or len(a["link"]) > LINK or "\n" in a["link"]:
        raise Refused(f"action: 'link' is one short sentence, {LINK} characters at most, tying this to what they asked. "
                      'Write "" only if they asked for exactly this action.')
    if s["shape"] != "A" and not a["link"].strip():
        raise Refused("action: they did not ask for this action in so many words, so 'link' cannot be empty. "
                      "Say in one short sentence how this answers what they asked.")
    opened(project_of(s, folder), a.get("files"), "action")
    seen = a.get("seen", {})
    need(seen, ("kind", "where"), "action, seen")
    if seen["kind"] not in SEEN:
        raise Refused(f"action, seen: 'kind' must be one of {', '.join(SEEN)}.")
    return a["question"]


def confirm(s: dict, folder: Path) -> str:
    """7. Say what will be shown and wait for a yes."""
    if not str(s.get("confirmed", "")).strip():
        link = s["action"]["link"].strip()
        does = s["action"]["start"].rstrip(".")
        does = does[0].lower() + does[1:]
        lines = ([link] if link else []) + [f"I'll show you what happens when {does}.", SAFE, "OK?"]
        raise say("\n".join(lines),
                  'write "confirmed": their reply, word for word, if it is a yes.\n'
                  'If they want something different, change that part of start.json, leave "confirmed" out, '
                  "and run this again.")
    return s["confirmed"]


STEPS = (asked, shape, where, look, narrow, action, confirm)


def check(folder: Path) -> int:
    """Print where the start has got to and what comes next. Returns READY only when all seven steps are done."""
    path = folder / "start.json"
    s = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if s.get("stopped") is True:
        print("STOPPED. The walk is over and nothing was made. Help them with what they asked, as you normally would.")
        return STOPPED

    done, result, message = {}, READY, "READY. Walk it."
    for number, step in enumerate(STEPS, 1):
        try:
            done[step.__name__] = step(s, folder)
        except Next as what:
            result, message = NEXT, f"NEXT: step {number}, {step.__name__}.\n{what}"
            break
        except Refused as why:
            result, message = REFUSED, f"REFUSED. {why}"
            break

    for number, step in enumerate(STEPS, 1):
        name = step.__name__
        state = f"done   {done[name]}" if name in done else "NEXT" if number == len(done) + 1 else "-"
        print(f"{number} {name:<8} {state}")

    print(f"\n{message}")
    return result


if __name__ == "__main__":
    sys.exit(check(Path(sys.argv[1]).resolve()))
