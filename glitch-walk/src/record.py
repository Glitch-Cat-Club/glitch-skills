"""Record what a command really prints, or what a file really holds.

Something with no web page still has things a person sees: what comes back in a terminal,
a line in a log, a file left behind. This saves one of those exactly as it is, so the walk
shows the real thing. Nothing is typed by hand.

    uv run python src/record.py <out.txt> -- <command> [arguments ...]
    uv run python src/record.py <out.txt> --file <path> [--match <text>] [--last <number>]

The first runs the command and saves everything it prints. Only run a command that changes nothing.
The second saves a file as it stands: with --match only the lines holding that text, with --last
only that many lines from the end.
Writes the text and beside it a .json file saying where it came from and when.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WAIT = 120      # how long a command may run before it is given up on


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 3 or args[1] not in ("--", "--file"):
        sys.exit(__doc__)
    out = Path(args[0])
    if args[1] == "--":
        command = args[2:]
        ran = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=WAIT)
        text, came_from = ran.stdout + ran.stderr, {"kind": "command", "from": " ".join(command), "exit": ran.returncode}
    else:
        path, rest = Path(args[2]), args[3:]
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if "--match" in rest:
            lines = [x for x in lines if rest[rest.index("--match") + 1] in x]
        if "--last" in rest:
            lines = lines[-int(rest[rest.index("--last") + 1]):]
        text, came_from = "\n".join(lines), {"kind": "file", "from": path.name}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    out.with_suffix(".json").write_text(json.dumps({**came_from, "when": datetime.now().isoformat(timespec="seconds")}),
                                        encoding="utf-8")
    print(f"recorded {out.name}: {len(text.splitlines())} lines from {came_from['from']}")


if __name__ == "__main__":
    main()
