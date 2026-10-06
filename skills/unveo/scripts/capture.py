"""Record the real web app (docs/10).

  capture.py probe --url <url> [--out unveo-out]   open the app once: status, title, login wall, screenshot
  capture.py check   [--out unveo-out]             validate capture/steps.json, flag risky steps, list the plan in plain words
  capture.py dry-run [--out unveo-out] [--scene sNN]   run the steps fast, no recording; screenshots + failure details

record arrives in Phase 5.
"""
import argparse, difflib, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, log, out_dir  # noqa: E402

VIEWPORT = {"width": 1920, "height": 1080}
LOGIN_PATH = re.compile(r"/(log-?in|sign-?in|auth)(/|$|\?)", re.I)

ACTIONS = {"goto", "click", "type", "select", "press", "scroll", "hover", "submit", "wait", "pause"}
NEEDS_TARGET = {"click", "type", "select", "hover", "submit"}
TARGET_KEYS = {"role", "name", "label", "placeholder", "text", "testid", "css"}
WAITS = {"network-idle", "selector", "url", "text", "ms"}
PAYMENT = re.compile(r"card|cvv|cvc|\bupi\b|checkout|payment|\bpay\b|pay now|purchase|\bbuy\b|billing", re.I)
DESTRUCTIVE = re.compile(r"delete|remove|\bsend\b|e-?mail|\bsms\b|publish|\bpost\b|transfer|withdraw|deploy|reset|cancel subscription", re.I)
ENV = re.compile(r"\$([A-Z_][A-Z0-9_]*)")
DEFAULT_TIMEOUT_MS = 10000


# ---------- rules (no browser)

def validate(steps):
    e = []
    if steps.get("version") != 1:
        e.append("version must be 1")
    if not str(steps.get("base_url", "")).startswith(("http://", "https://")):
        e.append("base_url must start with http:// or https://")
    scenes = steps.get("scenes") or {}
    if not scenes:
        e.append("scenes is empty")
    blocks = [("login", (steps.get("login") or {}).get("steps", []))]
    for sid, sc in scenes.items():
        if not re.fullmatch(r"s\d{2}", sid):
            e.append(f"scene id {sid} must look like s05")
        blocks.append((sid, ([sc["start"]] if sc.get("start") else []) + sc.get("steps", [])))
        if sc.get("end_on"):
            e += [f"{sid} end_on: {m}" for m in target_errors(sc["end_on"])]
    for sid, lst in blocks:
        for i, st in enumerate(lst):
            where = f"{sid} step {i}"
            do = st.get("do")
            if do not in ACTIONS:
                e.append(f"{where}: unknown action '{do}' (use one of {sorted(ACTIONS)})")
                continue
            if do in NEEDS_TARGET and not st.get("target"):
                e.append(f"{where}: {do} needs a target")
            if st.get("target"):
                e += [f"{where}: {m}" for m in target_errors(st["target"])]
            if do == "goto" and not st.get("url"):
                e.append(f"{where}: goto needs a url")
            if do == "type" and "text" not in st:
                e.append(f"{where}: type needs text")
            if do == "select" and not (st.get("value") or st.get("label")):
                e.append(f"{where}: select needs a value or a label")
            if do == "press" and not st.get("key"):
                e.append(f"{where}: press needs a key")
            if do == "scroll" and not (st.get("target") or st.get("by")):
                e.append(f"{where}: scroll needs a target or 'by'")
            if do == "wait":
                if st.get("for") not in WAITS:
                    e.append(f"{where}: wait 'for' must be one of {sorted(WAITS)}")
                elif st["for"] == "selector" and not st.get("target"):
                    e.append(f"{where}: wait for selector needs a target")
                elif st["for"] in ("url", "text", "ms") and "value" not in st:
                    e.append(f"{where}: wait for {st['for']} needs a value")
            if do == "pause" and "ms" not in st:
                e.append(f"{where}: pause needs ms")
    return e


def target_errors(t):
    bad = set(t) - TARGET_KEYS
    if bad:
        return [f"unknown target keys {sorted(bad)} (use role+name, label, placeholder, text, testid or css)"]
    if not set(t) & {"role", "label", "placeholder", "text", "testid", "css"}:
        return ["target needs one of role, label, placeholder, text, testid, css"]
    return []


def target_text(t):
    t = t or {}
    return t.get("name") or t.get("label") or t.get("text") or t.get("placeholder") or t.get("testid") or t.get("css") or ""


def flag(st):
    do = st.get("do")
    pool = " ".join(str(v) for v in (st.get("target") or {}).values()) + " " + str(st.get("url", ""))
    if do in ("click", "submit", "press", "type", "select", "goto") and PAYMENT.search(pool):
        return "payment"
    if do in ("click", "submit") and DESTRUCTIVE.search(pool):
        return "destructive"
    return None


def describe(st):
    do, name = st["do"], target_text(st.get("target"))
    if do == "goto":
        return f"open {st['url']}"
    if do == "type":
        shown = "••••" if st.get("secret") else f"\"{st['text']}\""
        return f"type {shown} into \"{name}\""
    if do == "select":
        return f"pick \"{st.get('label') or st.get('value')}\" in \"{name}\""
    if do == "press":
        return f"press {st['key']}"
    if do == "scroll":
        return f"scroll to \"{name}\"" if st.get("target") else f"scroll {'down' if st['by'] > 0 else 'up'} {abs(st['by'])} px"
    if do == "wait":
        w = st["for"]
        return {"network-idle": "wait for the page to settle", "selector": f"wait for \"{name}\"",
                "url": f"wait for the address to contain \"{st.get('value')}\"", "text": f"wait for \"{st.get('value')}\"",
                "ms": f"wait {st.get('value')} ms"}[w]
    if do == "pause":
        return f"pause {st['ms']} ms"
    return f"{do} \"{name}\""


def plan_line(st):
    line, f = describe(st), flag(st)
    if f == "payment":
        return f"⛔ {line} (payment, never automated)"
    if f == "destructive":
        return f"⚠️ {line} (destructive, {'approved' if st.get('approved') else 'skipped unless you approve'})"
    return line


def substitute(text, env):
    def rep(m):
        v = env.get(m.group(1))
        if not v:
            raise KeyError(m.group(1))
        return v
    return ENV.sub(rep, str(text))


def load_steps(out):
    path = Path(out) / "capture" / "steps.json"
    try:
        steps = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        emit("capture", ok=False, user_action=True, errors=[f"can't read {path}: {e}"])
    errs = validate(steps)
    if errs:
        emit("capture", ok=False, user_action=True, errors=errs, message=f"{len(errs)} problems in steps.json")
    return steps


def check_cmd(out):
    steps = load_steps(out)
    plan = {}
    if steps.get("login"):
        plan["login"] = [plan_line(s) for s in steps["login"]["steps"]]
    for sid, sc in sorted(steps["scenes"].items()):
        plan[sid] = [plan_line(s) for s in ([sc["start"]] if sc.get("start") else []) + sc.get("steps", [])]
    emit("capture", plan=plan, message="steps.json OK")


# ---------- browser

def locate(page, t):
    if "role" in t:
        return page.get_by_role(t["role"], name=t["name"]) if t.get("name") else page.get_by_role(t["role"])
    if "label" in t:
        return page.get_by_label(t["label"])
    if "placeholder" in t:
        return page.get_by_placeholder(t["placeholder"])
    if "text" in t:
        return page.get_by_text(t["text"])
    if "testid" in t:
        return page.get_by_test_id(t["testid"])
    return page.locator(t["css"])


def perform(page, st, base, env, dry):
    to = st.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    loc = locate(page, st["target"]).first if st.get("target") else None
    do = st["do"]
    if do == "goto":
        page.goto(urljoin(base, st["url"]), wait_until="load", timeout=to)
    elif do == "click":
        loc.click(timeout=to)
    elif do == "type":
        loc.fill(substitute(st["text"], env), timeout=to)  # ponytail: dry-run fills at once; record types per key
    elif do == "select":
        loc.select_option(**({"value": st["value"]} if st.get("value") else {"label": st["label"]}), timeout=to)
    elif do == "press":
        (loc.press(st["key"], timeout=to) if loc else page.keyboard.press(st["key"]))
    elif do == "scroll":
        loc.scroll_into_view_if_needed(timeout=to) if loc else page.mouse.wheel(0, st["by"])
    elif do == "hover":
        loc.hover(timeout=to)
    elif do == "submit":
        loc.click(timeout=to)
    elif do == "wait":
        w = st["for"]
        if w == "network-idle":
            page.wait_for_load_state("networkidle", timeout=to)
        elif w == "selector":
            loc.wait_for(state="visible", timeout=to)
        elif w == "url":
            page.wait_for_url(lambda u: st["value"] in u, timeout=to)
        elif w == "text":
            page.get_by_text(st["value"]).first.wait_for(state="visible", timeout=to)
        else:
            page.wait_for_timeout(min(st["value"], 300) if dry else st["value"])
    elif do == "pause":
        page.wait_for_timeout(min(st["ms"], 300) if dry else st["ms"])


CANDIDATES_JS = """() => [...document.querySelectorAll('a,button,input,select,textarea,label,[role],h1,h2,h3,th,option')]
  .map(e => (e.innerText || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.value || '').trim())
  .filter(t => t && t.length < 60)"""


def closest(page, wanted):
    try:
        texts = list(dict.fromkeys(page.evaluate(CANDIDATES_JS)))
    except Exception:
        return []
    return difflib.get_close_matches(wanted, texts, n=5, cutoff=0) if wanted else texts[:5]


def same_origin(url, base):
    a, b = urlparse(url), urlparse(base)
    return url.startswith(("about:", "data:")) or (a.scheme, a.netloc) == (b.scheme, b.netloc)


def env_names(steps):
    return sorted(set(ENV.findall(json.dumps(steps))))


def dry_run(out, only=None):
    from playwright.sync_api import sync_playwright, Error as PWError
    steps = load_steps(out)
    missing = [n for n in env_names(steps) if not os.environ.get(n)]
    if missing:
        emit("capture", ok=False, user_action=True, missing_env=missing,
             message=f"Set {' and '.join(missing)} in your terminal first (for example: export {missing[0]}=...), then run again.")
    base = steps["base_url"]
    d = out_dir(out) / "capture" / "dryrun"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.png"):
        old.unlink()
    results, failures, skipped = [], [], []
    blocks = ([("login", steps["login"]["steps"], None)] if steps.get("login") else []) + [
        (sid, sc.get("steps", []), sc) for sid, sc in sorted(steps["scenes"].items()) if not only or sid == only]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport=VIEWPORT).new_page()
        for sid, lst, sc in blocks:
            t0, err, idx = time.time(), None, None
            try:
                if sc and sc.get("start"):
                    target = urljoin(base, sc["start"]["url"])
                    if page.url.rstrip("/") != target.rstrip("/"):
                        perform(page, sc["start"], base, os.environ, True)
                elif sid != "login" and page.url == "about:blank":
                    page.goto(base, wait_until="load")
                for idx, st in enumerate(lst):
                    f = flag(st)
                    if f == "payment" or (f == "destructive" and not st.get("approved")):
                        skipped.append({"scene": sid, "step": idx, "flag": f, "what": describe(st)})
                        continue
                    perform(page, st, base, os.environ, True)
                    if not same_origin(page.url, base):
                        raise RuntimeError(f"left the app: went outside {base} to {page.url}")
                if sc and sc.get("end_on"):
                    idx = "end_on"
                    locate(page, sc["end_on"]).first.wait_for(state="visible", timeout=5000)
            except (PWError, RuntimeError, KeyError) as e:
                msg = str(e).splitlines()[0] if str(e) else repr(e)
                wanted = target_text((lst[idx] if isinstance(idx, int) and idx < len(lst) else {}).get("target")
                                     if idx != "end_on" else sc.get("end_on"))
                shot = d / f"{sid}-fail.png"
                page.screenshot(path=str(shot))
                err = {"scene": sid, "step": idx, "error": msg[:300], "closest": closest(page, wanted), "screenshot": str(shot)}
                failures.append(err)
            if not err:
                page.screenshot(path=str(d / f"{sid}.png"))
            results.append({"scene": sid, "ok": err is None, "seconds": round(time.time() - t0, 1)})
        browser.close()
    sheet = contact_sheet(d)
    res = {"scenes": [r for r in results if r["scene"] != "login"], "failures": failures, "skipped": skipped,
           "outputs": [str(sheet)] if sheet else []}
    (d / "result.json").write_text(json.dumps(res, indent=2))
    if failures:
        emit("capture", ok=False, user_action=True, message=f"{len(failures)} scene(s) failed the dry run", **res)
    emit("capture", message=f"dry run passed: {len(res['scenes'])} scene(s)", **res)


def contact_sheet(d):
    from PIL import Image, ImageDraw, ImageFont
    shots = sorted(d.glob("*.png"))
    shots = [s for s in shots if s.name != "sheet.png"]
    if not shots:
        return None
    cols, w, h = 3, 640, 360
    rows = -(-len(shots) // cols)
    sheet = Image.new("RGB", (cols * w, rows * (h + 40)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, s in enumerate(shots):
        x, y = (i % cols) * w, (i // cols) * (h + 40)
        sheet.paste(Image.open(s).convert("RGB").resize((w - 8, h - 8)), (x + 4, y + 4))
        fail = s.stem.endswith("-fail")
        draw.text((x + 8, y + h + 6), s.stem + ("  FAILED" if fail else "  OK"), fill="#dc2626" if fail else "#15803d",
                  font=ImageFont.load_default(size=22))
    path = d / "sheet.png"
    sheet.save(path)
    return path


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
    for name in ("check", "dry-run"):
        sp = sub.add_parser(name)
        sp.add_argument("--scene")
    for sp in sub.choices.values():
        sp.add_argument("--out", default="unveo-out")
    a = ap.parse_args()
    if a.cmd == "probe":
        probe(a.url, a.out)
    elif a.cmd == "check":
        check_cmd(a.out)
    else:
        dry_run(a.out, a.scene)


if __name__ == "__main__":
    main()
