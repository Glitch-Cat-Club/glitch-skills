"""Build one walk into one page.

    uv run python src/build.py <walk folder>

The walk folder holds walk.json (what the model filled in) and shots/ (pictures taken by
capture.py, each with its measurements). This build does everything that must not be left
to the model: it pulls every line of code from the real file, takes every position from
the capture, numbers the steps and refuses a walk that breaks a rule. It writes
<walk folder>/walk.html, one file with nothing beside it, so it can be opened or sent as it is.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent
SHAPES = {
    "A": "What happens when I do this?",
    "B": "What is this part doing?",
    "C": "How does this whole thing work?",
    "D": "Why did that happen?",
    "E": "What does this on my screen mean?",
    "F": "Explain this idea, in my system",
    "G": "What changed?",
}
STATES = ("do", "see", "wait")
ABOUT = ("what", "who", "on", "address")
STEP = ("name", "title", "why", "here", "icon")
SHOWN = 20   # the most lines of a recording one screen shows
WIDE = 160    # a recorded line longer than this is cut and ends in three dots
SAY = 100    # the longest the line for one thing you do or see may be: one line of the list under Jump to


class Refused(Exception):
    """The walk breaks a rule. The message says which, in words the model can act on."""


def need(thing: dict, fields, where: str) -> None:
    for f in fields:
        if not str(thing.get(f, "")).strip():
            raise Refused(f"{where}: '{f}' is missing or empty.")


def version(root: Path, path: str) -> str:
    """The short version of a file in its project's history, or '' when it has none."""
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%h", "--", path],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def pull(root: Path, files: dict, c: dict, where: str) -> dict:
    """Read the code from the real file. Typed code is never accepted."""
    if "text" in c:
        raise Refused(f"{where}: code was typed into the walk. Give the file and line numbers; the build reads the file.")
    need(c, ("file", "start", "end", "plain"), where)
    if c["file"] not in files:
        raise Refused(f"{where}: file '{c['file']}' is not in the walk's list of files.")
    path = files[c["file"]]["path"]
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    start, end = int(c["start"]), int(c["end"])
    if not 1 <= start <= end <= len(lines):
        raise Refused(f"{where}: lines {start} to {end} are not in {path}, which has {len(lines)} lines.")
    if end - start + 1 > 16:
        raise Refused(f"{where}: {end - start + 1} lines is too much to show at once. Show 16 or fewer, around the lines that do the thing.")
    marks = [int(m) for m in c.get("marks", [])]
    if not marks or any(not start <= m <= end for m in marks):
        raise Refused(f"{where}: 'marks' must name at least one line between {start} and {end}: the lines that do the thing.")
    block = lines[start - 1:end]
    indent = min((len(x) - len(x.lstrip()) for x in block if x.strip()), default=0)
    return {"file": c["file"], "path": path, "version": files[c["file"]]["version"], "start": start,
            "marks": marks, "plain": c["plain"], "text": "\n".join(x[indent:] for x in block)}


def lit(code: list) -> set:
    """The lines a step lights, across all its pieces of code."""
    return {(c["file"], line) for c in code for line in c["marks"]}


def label(h: dict, code: list, before, letters: int, count: int, where: str) -> str:
    """Where a step sits in the order.

    A number: it happens once, after the step before it has finished.
    A number and a letter (3a, 3b): it happens inside or alongside step 3. The walk marks it "inside".
    Nothing: it did not happen in this walk and would only under a condition. The walk marks it "only_if".
    """
    only_if, inside = str(h.get("only_if", "")).strip(), bool(h.get("inside"))
    if only_if and inside:
        raise Refused(f"{where}: it is marked both 'inside' and 'only_if'. A step that did not happen this time "
                      "is not inside one that did. Keep one.")
    if only_if:
        return ""
    if inside:
        if before is None:
            raise Refused(f"{where}: it is marked 'inside', but no numbered step comes before it in this moment.")
        return f"{before['label']}{chr(ord('a') + letters)}"
    if before and lit(code) and lit(code) <= lit(before["code"]):
        raise Refused(f"{where}: it lights only lines that step {before['label']} already lights, so it happens "
                      'inside that step and not after it. Mark it "inside": true.')
    return str(count + 1)


def printed(folder: Path, sc: dict, where: str) -> dict:
    """What a command really printed or a file really held, read from what record.py saved. Typed lines are never accepted."""
    if "lines" in sc:
        raise Refused(f"{where}: lines were typed into a screen that names an 'output'. Give the line numbers; the build reads the recording.")
    need(sc, ("output", "source", "start", "end"), where)
    txt, meta = folder / "shots" / f"{sc['output']}.txt", folder / "shots" / f"{sc['output']}.json"
    if not txt.exists() or not meta.exists():
        raise Refused(f"{where}: shots/{sc['output']}.txt and its .json are not there. Record it with record.py.")
    m, lines = json.loads(meta.read_text(encoding="utf-8")), txt.read_text(encoding="utf-8").splitlines()
    start, end = int(sc["start"]), int(sc["end"])
    if not 1 <= start <= end <= len(lines):
        raise Refused(f"{where}: lines {start} to {end} are not in shots/{sc['output']}.txt, which has {len(lines)} lines.")
    if end - start + 1 > SHOWN:
        raise Refused(f"{where}: {end - start + 1} lines is too much to show at once. Show {SHOWN} or fewer, around what this moment is about.")
    marks = [int(x) for x in sc.get("marks", [])]
    if any(not start <= x <= end for x in marks):
        raise Refused(f"{where}: 'marks' must name lines between {start} and {end}: the ones this moment is about.")
    cut = lambda x: x if len(x) <= WIDE else x[:WIDE].rstrip() + " ..."
    top = [{"t": "prompt", "v": sc["typed"]}, {"t": "", "v": ""}] if str(sc.get("typed", "")).strip() else []
    came = [{"t": "tool" if m["kind"] == "command" else "dim", "v": m["from"]}]
    body = [{"t": "dim" if marks and n not in marks else "", "v": cut(x)} for n, x in enumerate(lines[start - 1:end], start)]
    return {"source": sc["source"], "lines": top + came + body, "place": sc.get("place"), "real": True}


def screen(folder: Path, sc: dict, where: str) -> dict:
    """A picture and its measured parts, what a real run printed, or a drawn screen that says why it is drawn."""
    if "output" in sc:
        return printed(folder, sc, where)
    if "shot" not in sc:
        need(sc, ("source",), where)
        if str(sc.get("typed", "")).strip() and "lines" not in sc:
            return {"source": sc["source"], "lines": [{"t": "prompt", "v": sc["typed"]}], "place": sc.get("place")}
        if not sc.get("lines") or any(not isinstance(x, dict) or "v" not in x for x in sc["lines"]):
            raise Refused(f"{where}: a screen with no picture and no recording shows what they 'typed' and nothing else, "
                          "or is drawn from 'lines', each with a 't' and a 'v'. Either way its 'source' says why.")
        return {"source": sc["source"], "lines": sc["lines"], "place": sc.get("place")}
    need(sc, ("source",), where)
    jpg, meta = folder / "shots" / f"{sc['shot']}.jpg", folder / "shots" / f"{sc['shot']}.json"
    if not jpg.exists() or not meta.exists():
        raise Refused(f"{where}: shots/{sc['shot']}.jpg and its .json are not there. Take it with capture.py.")
    m = json.loads(meta.read_text(encoding="utf-8"))
    spots = []
    for p in sc.get("parts", []):
        need(p, ("part", "name", "says"), f"{where}, part")
        if p["part"] not in m["boxes"]:
            raise Refused(f"{where}: part '{p['part']}' was not measured by the capture. Measured: {', '.join(m['boxes'])}.")
        spots.append({"box": m["boxes"][p["part"]], "name": p["name"], "says": p["says"], "here": bool(p.get("here"))})
    unlisted = set(m["boxes"]) - {p["part"] for p in sc.get("parts", [])}
    if unlisted:
        raise Refused(f"{where}: measured on the screen but not explained: {', '.join(sorted(unlisted))}. Every part gets a line.")
    data = "data:image/jpeg;base64," + base64.b64encode(jpg.read_bytes()).decode("ascii")
    return {"source": sc["source"], "src": data, "size": m["size"], "spots": spots, "place": sc.get("place")}


def build(folder: Path) -> Path:
    w = json.loads((folder / "walk.json").read_text(encoding="utf-8"))
    need(w, ("question", "shape", "place", "root", "run"), "the walk")
    if w["shape"] not in SHAPES:
        raise Refused(f"the walk: 'shape' must be one of {', '.join(SHAPES)}.")
    need(w.get("about", {}), ABOUT, "what you're looking at")
    root = (folder / w["root"]).resolve()
    if not root.is_dir():
        raise Refused(f"the walk: 'root' does not point at a folder ({root}).")
    files = {}
    for f in w.get("files", []):
        need(f, ("id", "path", "kind", "says"), "a file")
        if not (root / f["path"]).is_file():
            raise Refused(f"a file: {f['path']} is not in {root}.")
        files[f["id"]] = {**f, "version": version(root, f["path"])}
    if not files:
        raise Refused("the walk: it names no files.")
    if not w.get("moments"):
        raise Refused("the walk: it has nothing you do or see.")

    n, happened, names, moments, used = 0, 0, set(), [], set()
    for mi, m in enumerate(w["moments"], 1):
        where = f"moment {mi}"
        need(m, ("state", "say"), where)
        if m["state"] not in STATES:
            raise Refused(f"{where}: 'state' must be one of {', '.join(STATES)}.")
        if len(m["say"]) > SAY:
            raise Refused(f"{where}: 'say' is too long to sit on one line of the list. Say it in one shorter sentence: "
                          "who does what, or what they see. The detail belongs in the steps.")
        if "screen" not in m:
            raise Refused(f"{where}: something you do or see needs its screen, or a drawn one that says why.")
        if m["state"] != "do" and "typed" in m["screen"] and not {"shot", "output", "lines"} & set(m["screen"]):
            raise Refused(f"{where}: it is marked '{m['state']}' but its screen holds only something typed, so nothing was seen. "
                          "It is not a thing they see. Put what happens in the steps of the one before and say in 'unsure' what was not seen.")
        steps, before, letters = [], None, 0
        for h in m.get("hidden", []):
            sw = f"the step '{h.get('name', 'unnamed')}'"
            need(h, STEP, sw)
            if h["name"] in names:
                raise Refused(f"{sw}: two steps share the name '{h['name']}'. Each step has its own.")
            names.add(h["name"])
            if not h.get("files") or any(f not in files for f in h["files"]):
                raise Refused(f"{sw}: 'files' must name at least one file from the walk's list.")
            if not h.get("code") and not h.get("unsure"):
                raise Refused(f"{sw}: a step shows its code, or says under 'unsure' why it cannot.")
            used.update(h["files"])
            code = [pull(root, files, c, sw) for c in h.get("code", [])]
            step = {"key": len(names), "label": label(h, code, before, letters, n, sw), "inside": bool(h.get("inside")),
                    "only_if": str(h.get("only_if", "")).strip(), "size": h.get("size", "big"), "icon": h["icon"],
                    "name": h["name"], "title": h["title"], "why": h["why"], "here": h["here"], "files": h["files"],
                    "unsure": h.get("unsure"), "code": code}
            if step["label"].isdigit():
                n, before, letters = n + 1, step, 0
            elif step["inside"]:
                letters += 1
            happened += bool(step["label"])
            steps.append(step)
        moments.append({"state": m["state"], "say": m["say"], "unsure": m.get("unsure"),
                        "screen": screen(folder, m["screen"], where), "hidden": steps, "quiet": m.get("quiet")})
        if not steps and not m.get("quiet"):
            raise Refused(f"{where}: nothing happens out of sight here, so say that in 'quiet'. A gap is never left empty.")
    unused = set(files) - used
    if unused:
        raise Refused(f"the walk: listed but never used by a step: {', '.join(sorted(unused))}.")

    story = {"question": w["question"], "shape": SHAPES[w["shape"]], "place": w["place"], "run": w["run"],
             "about": w["about"], "files": list(files.values()),
             "moments": moments, "silent": w.get("silent", []), "ask": w.get("ask", [])}
    logo = "data:image/png;base64," + base64.b64encode((SRC / "logo.png").read_bytes()).decode("ascii")
    css = f":root {{ --logo: url({logo}); }}\n" + (SRC / "story.css").read_text(encoding="utf-8")
    js = (SRC / "story.js").read_text(encoding="utf-8")
    data = json.dumps(story, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{w['question']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Changa+One&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{css}</style>
</head>
<body>
<div class="wrap" id="story"></div>
<script>window.STORY = {data};</script>
<script>
{js}</script>
</body>
</html>
"""
    out = folder / "walk.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"built {out.name}: {len(moments)} things you do or see, {happened} steps out of sight, {len(files)} files")
    return out


if __name__ == "__main__":
    try:
        build(Path(sys.argv[1]).resolve())
    except Refused as e:
        print(f"REFUSED. {e}")
        sys.exit(1)
