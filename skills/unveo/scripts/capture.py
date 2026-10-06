"""Record the real web app (docs/10).

  capture.py probe --url <url> [--out unveo-out]   open the app once: status, title, login wall, screenshot

dry-run and record arrive in later phases.
"""
import argparse, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, out_dir  # noqa: E402

VIEWPORT = {"width": 1920, "height": 1080}
LOGIN_PATH = re.compile(r"/(log-?in|sign-?in|auth)(/|$|\?)", re.I)


def probe(url, out):
    from playwright.sync_api import sync_playwright, Error as PWError
    shot = out_dir(out) / "capture" / "probe.png"
    shot.parent.mkdir(exist_ok=True)
    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        try:
            resp = page.goto(url, wait_until="load", timeout=20000)
        except PWError as e:
            browser.close()
            emit("probe", ok=False, user_action=True, url=url, status=None,
                 message=f"I couldn't open {url} ({str(e).splitlines()[0]}). Is the app running and the link right?")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWError:
            log("network never went idle; using the page as it is")
        status = resp.status if resp else None
        final_url = page.url
        title = page.title()
        login_wall = bool(LOGIN_PATH.search(final_url)) or page.locator("input[type=password]:visible").count() > 0
        page.screenshot(path=str(shot))
        browser.close()
    result = dict(url=url, final_url=final_url, status=status, title=title, login_wall=login_wall,
                  load_s=round(time.time() - t0, 1), outputs=[str(shot)])
    if status and status >= 400:
        emit("probe", ok=False, user_action=True, message=f"{url} answered with HTTP {status}.", **result)
    emit("probe", message=f"Loaded \"{title}\" in {result['load_s']} s" + (" (login needed)" if login_wall else ""), **result)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("probe")
    pr.add_argument("--url", required=True)
    pr.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    if a.cmd == "probe":
        probe(a.url, a.out)


if __name__ == "__main__":
    main()
