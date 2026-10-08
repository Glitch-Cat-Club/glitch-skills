"""Look at a built walk the way a person would and report what is wrong with how it draws.

    uv run --with playwright python tests/check_page.py <walk.html> <folder for the pictures>

Opens the page wide and upright, opens every step, opens each screen full size and takes
pictures of all of it in slices short enough to read. Prints anything a machine can tell is
wrong: an error on the page, the page scrolling sideways, text cut off, a numbered spot that
has fallen outside its picture, a picture that did not load.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

WIDTHS = {"wide": 1400, "upright": 420}
SLICE = 1800

FAULTS = """() => {
  const out = [], vw = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth > vw + 2) out.push('the page scrolls sideways: ' + document.documentElement.scrollWidth + ' wide in a ' + vw + ' window');
  for (const n of document.querySelectorAll('body *')) {
    const r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    if (!r.width || cs.visibility === 'hidden') continue;
    const label = n.tagName.toLowerCase() + (n.className && n.className.baseVal === undefined ? '.' + String(n.className).split(' ').join('.') : '') + ' "' + (n.textContent || '').trim().slice(0, 40) + '"';
    if (r.right > vw + 2 && !n.closest('pre, .zoom')) out.push('runs off the right edge: ' + label);
    if (!n.children.length && n.scrollWidth > n.clientWidth + 2 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' && cs.textOverflow !== 'ellipsis' && !n.closest('pre')) out.push('text cut off: ' + label);
  }
  for (const img of document.images) if (!img.complete || !img.naturalWidth) out.push('picture did not load: ' + (img.alt || img.src.slice(0, 40)));
  for (const fig of document.querySelectorAll('figure.screen')) {
    const img = fig.querySelector('img'); if (!img) continue;
    const box = img.getBoundingClientRect();
    for (const s of fig.querySelectorAll('[data-spot]')) {
      const r = s.getBoundingClientRect();
      if (r.left < box.left - 9 || r.top < box.top - 9 || r.right > box.right + 9 || r.bottom > box.bottom + 9) out.push('a spot sits outside its picture: ' + (s.textContent || '').trim().slice(0, 20));
    }
  }
  return [...new Set(out)];
}"""


def slices(page, out: Path, name: str) -> int:
    height = page.evaluate("document.documentElement.scrollHeight")
    width = page.viewport_size["width"]
    count = 0
    for top in range(0, height, SLICE):
        count += 1
        page.screenshot(path=str(out / f"{name}-{count:02}.png"), full_page=True,
                        clip={"x": 0, "y": top, "width": width, "height": min(SLICE, height - top)})
    return count


def main() -> None:
    html, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for name, width in WIDTHS.items():
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(html.as_uri())
            page.wait_for_timeout(800)
            found = {"closed": page.evaluate(FAULTS)}
            slices(page, out, f"{name}-closed")
            steps = page.locator(".row[role=button]").count()
            for i in range(steps):
                page.locator(".row[role=button]").nth(i).click()
            page.wait_for_timeout(300)
            found["every step open"] = page.evaluate(FAULTS)
            found["pictures"] = slices(page, out, f"{name}-open")
            screens = page.locator("figure.screen:not(.big)").count()
            for i in range(screens):
                page.locator("figure.screen:not(.big)").nth(i).click()
                page.wait_for_timeout(300)
                page.screenshot(path=str(out / f"{name}-fullsize-{i + 1}.png"))
                found[f"screen {i + 1} full size"] = page.evaluate(FAULTS)
                page.keyboard.press("Escape")
            found["errors"], found["steps"], found["screens"] = errors, steps, screens
            report[name] = found
            page.close()
        browser.close()
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
