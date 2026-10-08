"""Capture one screen of a web page and measure where each named part sits on it.

The picture and the positions come from the same page load, so a spot drawn on the
picture can never drift from the thing it marks. Nothing is typed by hand.

    uv run --with playwright --with pillow python src/capture.py <url> <out.jpg> <until-selector> [--do "<javascript>"] [--height <pixels>] name=selector ...

`until-selector` is the last thing the picture has to include; the picture is cut a
little below it. `--do` runs a line of JavaScript on the page first, to put it in a
state without sending anything (the walk says so wherever it is used). `--height` sets
how tall the window is, for a page that centres itself in the window and would otherwise
be photographed with empty space above it.
Writes the picture and beside it a .json file with the picture's size and each part's
box as percentages of the picture (left, top, width, height).
"""
import json
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

WIDTH = 902        # the window width every capture uses, so pictures line up across a walk
DENSITY = 2        # twice the pixels, so the full-size view stays sharp
MARGIN = 36        # space kept under the last thing in the picture
HEIGHT = 1400      # how tall the window is, unless --height says otherwise
QUIET = 8000       # how long to wait for a page to finish loading before taking it as it is
LOOSE = 90         # a piece that only holds others is questioned when what can be seen fills less than this much of it

# How much of a piece can be seen. A piece that draws something itself gives nothing back. One that only holds
# other pieces gives how much of its width and height the things drawn inside it fill, so an outline is never
# put round empty space without the model being told.
FILLED = """(e) => {
  const draws = (n) => { const c = getComputedStyle(n);
    return c.backgroundColor !== 'rgba(0, 0, 0, 0)' || c.backgroundImage !== 'none' || parseFloat(c.borderTopWidth) > 0 || c.boxShadow !== 'none'
      || ['IMG', 'CANVAS', 'SVG', 'VIDEO', 'INPUT', 'BUTTON', 'SELECT', 'TEXTAREA'].includes(n.tagName.toUpperCase())
      || [...n.childNodes].some((t) => t.nodeType === 3 && t.textContent.trim()); };
  const r = e.getBoundingClientRect();
  if (draws(e) || !r.width || !r.height) return null;
  let left = 1e9, top = 1e9, right = -1e9, bottom = -1e9;
  for (const n of e.querySelectorAll('*')) { const q = n.getBoundingClientRect();
    if (q.width && q.height && draws(n)) { left = Math.min(left, q.left); top = Math.min(top, q.top); right = Math.max(right, q.right); bottom = Math.max(bottom, q.bottom); } }
  if (right < left) return [0, 0];
  return [Math.round(100 * (Math.min(right, r.right) - Math.max(left, r.left)) / r.width),
          Math.round(100 * (Math.min(bottom, r.bottom) - Math.max(top, r.top)) / r.height)];
}"""


def main() -> None:
    args = sys.argv[1:]
    do, window = None, HEIGHT
    if "--do" in args:
        i = args.index("--do")
        do = args[i + 1]
        del args[i:i + 2]
    if "--height" in args:
        i = args.index("--height")
        window = int(args[i + 1])
        del args[i:i + 2]
    url, out, until = args[0], Path(args[1]), args[2]
    parts = [a.split("=", 1) for a in args[3:]]
    with sync_playwright() as p:
        # a page opened straight from a folder may load its own script from that folder; without this a built page comes up blank
        browser = p.chromium.launch(channel="chrome", headless=True, args=["--allow-file-access-from-files"])
        page = browser.new_page(viewport={"width": WIDTH, "height": window}, device_scale_factor=DENSITY)
        page.goto(url, wait_until="load")
        try:                                    # some pages never go quiet; those are taken as they stand
            page.wait_for_load_state("networkidle", timeout=QUIET)
        except Exception:
            pass
        page.evaluate("document.fonts.ready")
        if do:
            page.evaluate(do)
        page.wait_for_timeout(800)
        last = page.locator(until).first.bounding_box()
        height = round(last["y"] + last["height"] + MARGIN)
        boxes = {}
        for name, selector in parts:
            b = page.locator(selector).first.bounding_box()
            if b is None:
                raise SystemExit(f"not on the page: {name} ({selector})")
            filled = page.locator(selector).first.evaluate(FILLED)
            if filled is not None and min(filled) < LOOSE:
                print(f"CHECK {name}: this piece draws nothing itself. It only holds other pieces, and what can be seen in it "
                      f"fills {filled[0]}% of its width and {filled[1]}% of its height. If you meant something inside it, name that instead.")
            boxes[name] = [round(100 * b["x"] / WIDTH, 2), round(100 * b["y"] / height, 2),
                           round(100 * b["width"] / WIDTH, 2), round(100 * b["height"] / height, 2)]
        png = out.with_suffix(".png")
        # full_page lets the picture run past the bottom of the window, so a tall page is never cut short
        page.screenshot(path=str(png), type="png", full_page=True, clip={"x": 0, "y": 0, "width": WIDTH, "height": height})
        browser.close()
    Image.open(png).convert("RGB").save(out, quality=88, optimize=True, progressive=True)
    png.unlink()
    out.with_suffix(".json").write_text(json.dumps({"size": [WIDTH, height], "boxes": boxes}, indent=1), encoding="utf-8")
    print(f"saved {out.name}: {WIDTH} x {height}, {len(boxes)} parts measured")


if __name__ == "__main__":
    main()
