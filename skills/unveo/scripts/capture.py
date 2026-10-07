"""Record the real web app (docs/10).

  capture.py probe --url <url> [--out unveo-out/.work]   open the app once: status, title, login wall, screenshot
  capture.py check   [--out unveo-out/.work]             validate capture/steps.json, flag risky steps, list the plan in plain words
  capture.py dry-run [--out unveo-out/.work] [--scene sNN]   run the steps fast, no recording; screenshots + failure details

  capture.py record  [--out unveo-out/.work] [--scene sNN]   record each capture scene, paced to its voice clip
"""
import argparse, asyncio, base64, difflib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, ffmpeg_exe, log, out_dir, read_json  # noqa: E402

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
CURSOR_JS = Path(__file__).resolve().parents[1] / "templates" / "cursor.js"
GUIDE_JS = Path(__file__).resolve().parents[1] / "templates" / "guide.js"
LOGIN_BAR = "Please log in here, any way you like. unveo carries on by itself once you're in."
HIDDEN_CHECK_S = float(os.environ.get("UNVEO_HIDDEN_CHECK_S", 8))  # how long the hidden browser may take to show it's logged in


def session_script(origin, pairs):
    """Restore the visible window's sessionStorage in the hidden browser (storage_state doesn't carry it)."""
    return (f"if (location.origin === {json.dumps(origin)}) for (const [k, v] of {json.dumps(pairs)}) "
            "if (sessionStorage.getItem(k) === null) sessionStorage.setItem(k, v);")


def hidden_session_sync(p, vctx, vpage, steps, base):
    b = None
    try:
        state = vctx.storage_state(indexed_db=True)
        origin, pairs = vpage.evaluate("location.origin"), vpage.evaluate("() => Object.entries(sessionStorage)")
        b = p.chromium.launch()
        c = b.new_context(storage_state=state, **ctx_args(steps))
        c.add_init_script(script=session_script(origin, pairs))
        pg = c.new_page()
        pg.goto(urljoin(base, steps["login"]["start"]), wait_until="load")
        perform(pg, {**login_wait_step(steps), "timeout_ms": int(HIDDEN_CHECK_S * 1000)}, base, os.environ, False)
        return b, c, pg
    except Exception as e:
        log(f"the login didn't carry over to a hidden browser ({str(e).splitlines()[0][:120]}); rehearsing in the visible window")
        if b:
            b.close()
        return None


async def hidden_session(p, vctx, vpage, steps, base):
    """Copy the person's login into a headless browser and check it's accepted there. None = record in their window."""
    b = None
    try:
        state = await vctx.storage_state(indexed_db=True)
        origin = await vpage.evaluate("location.origin")
        pairs = await vpage.evaluate("() => Object.entries(sessionStorage)")
        b = await p.chromium.launch()
        c = await b.new_context(storage_state=state, **ctx_args(steps))
        await c.add_init_script(script=session_script(origin, pairs))
        await c.add_init_script(path=str(CURSOR_JS))
        pg = await c.new_page()
        await pg.goto(urljoin(base, steps["login"]["start"]), wait_until="load")
        await aperform(pg, {**login_wait_step(steps), "timeout_ms": int(HIDDEN_CHECK_S * 1000)}, base, os.environ)
        return b, c, pg
    except Exception as e:
        log(f"the login didn't carry over to a hidden browser ({str(e).splitlines()[0][:120]}); recording in the visible window")
        if b:
            await b.close()
        return None
EARLY_S, MIN_GAP_S, GLIDE_MS = 0.3, 0.4, 550
SETTLE_S = 0.8  # after the last action the page holds this long, so a cut never lands on a click


ZOOM_EASE_S, ZOOM_HOLD_S, ZOOM_SCALE = 0.6, 2.0, 1.6


def has_zoom(steps):
    return any(st.get("zoom") for sc in (steps.get("scenes") or {}).values() for st in sc.get("steps", []))


def ctx_args(steps, hi_res=False):
    """1920x1080 at 100% by default: the CDP screencast captures CSS pixels, so this is the only size that's
    native-sharp (measured 7 Oct 2026). viewport.zoom > 1 enlarges the UI with the real layout, but frames are
    then upscaled and a little softer. CSS zoom is not used: it breaks full-height layouts and iframes.
    Readability for small details comes from step zooms (zoom_crop)."""
    z = float((steps.get("viewport") or {}).get("zoom", 1.0))
    return {"viewport": {"width": round(1920 / z), "height": round(1080 / z)}, "device_scale_factor": z}


def zoom_k(t, zooms):
    """(how far into a zoom we are, 0..1 eased in-out; that zoom) at time t, or (0, None)."""
    for z in zooms:
        t0 = z["t_s"]
        ease, hold = z.get("ease_s", ZOOM_EASE_S), z.get("hold_s", ZOOM_HOLD_S)
        if t < t0 or t > t0 + 2 * ease + hold:
            continue
        k = min(1.0, (t - t0) / ease) if t < t0 + ease + hold else max(0.0, 1 - (t - t0 - ease - hold) / ease)
        return (4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2), z
    return 0.0, None


def zoom_crop(t, zooms, W, H):
    """The part of a W x H frame to show at time t: eases in on the zoom's box, holds, eases back out (docs/15 A9)."""
    k, z = zoom_k(t, zooms)
    if z:
        s = 1 + (z["scale"] - 1) * k
        w, h = round(W / s), round(H / s)
        bx, by, bw, bh = z["box"]
        x = min(max(0, round(bx + bw / 2 - w / 2)), W - w)
        y = min(max(0, round(by + bh / 2 - h / 2)), H - h)
        return x, y, w, h
    return 0, 0, W, H


def spotlight(img, k, box, pad=18):
    """Dim everything but the zoom's target (a "spotlight" display): the page stays still, the light moves."""
    from PIL import Image, ImageDraw
    if k <= 0.001:
        return img
    shade = Image.new("L", img.size, round(150 * k))
    bx, by, bw, bh = box
    ImageDraw.Draw(shade).rounded_rectangle((bx - pad, by - pad, bx + bw + pad, by + bh + pad), 14, fill=0)
    return Image.composite(Image.new("RGB", img.size, "#000000"), img, shade)


# ---------- rules (no browser)

def validate(steps):
    import looks
    e = [f"{sid}: display must be one of {', '.join(looks.DISPLAYS)}" for sid, sc in (steps.get("scenes") or {}).items()
         if sc.get("display") and sc["display"] not in looks.DISPLAYS]
    if steps.get("version") != 1:
        e.append("version must be 1")
    if not str(steps.get("base_url", "")).startswith(("http://", "https://")):
        e.append("base_url must start with http:// or https://")
    scenes = steps.get("scenes") or {}
    if not scenes:
        e.append("scenes is empty")
    login = steps.get("login") or {}
    if login.get("mode") == "manual":
        if not login.get("start"):
            e.append("login.start (the page where the person logs in) is required for a manual login")
        u = login.get("until") or {}
        if u.get("for") not in WAITS - {"ms", "network-idle"}:
            e.append("login.until must say how to tell the person is logged in: {\"for\": \"text\"|\"url\"|\"selector\", ...}")
        elif u["for"] == "selector" and not u.get("target"):
            e.append("login.until for selector needs a target")
        elif u["for"] in ("url", "text") and "value" not in u:
            e.append(f"login.until for {u['for']} needs a value")
    blocks = [("login", login.get("steps", []))]
    for sid, sc in scenes.items():
        zs = [st for st in sc.get("steps", []) if st.get("zoom")]
        if len(zs) > 1:
            e.append(f"{sid}: only one zoom per scene, so it stays subtle ({len(zs)} found)")
        for st in zs:
            if not st.get("target"):
                e.append(f"{sid}: a zoom needs a target to zoom in on")
            if isinstance(st["zoom"], dict) and not 1.2 <= float(st["zoom"].get("scale", ZOOM_SCALE)) <= 2.0:
                e.append(f"{sid}: zoom scale must be between 1.2 and 2.0 (more gets blurry)")
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
    if do in ("click", "submit") and (DESTRUCTIVE.search(pool) or st.get("once")):  # once: can't be undone (one response per person)
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


def is_manual(steps):
    return (steps.get("login") or {}).get("mode") == "manual"


def login_plan(login):
    u = login.get("until", {})
    sign = u.get("value") or target_text(u.get("target"))
    return (f"🔑 a browser window opens at {login.get('start')}; you log in yourself (any method, even Google or OTP); "
            f"unveo carries on once it sees \"{sign}\"")


PROFILE_ARGS = {"ignore_default_args": ["--enable-automation"], "args": ["--disable-blink-features=AutomationControlled"]}


def profile_dir(steps):
    """One browser profile per site, so a login can be remembered between the dry run and the recording."""
    host = re.sub(r"[^\w.-]", "_", urlparse(steps["base_url"]).netloc)
    d = Path(os.environ.get("UNVEO_HOME", Path.home() / ".unveo")) / "profiles" / host
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def headed():
    return os.environ.get("UNVEO_FORCE_HEADLESS") != "1"  # tests run headless; real manual logins need a window


def login_wait_step(steps):
    login = steps["login"]
    return {"do": "wait", **login["until"], "timeout_ms": int(login.get("timeout_s", 600) * 1000)}


LOGIN_HELP = ("Waiting for you to log in in the browser window that just opened (any login method works). "
              "unveo continues by itself once you're in; don't close the window.")


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
        plan["login"] = ([login_plan(steps["login"])] if is_manual(steps) else [plan_line(s) for s in steps["login"]["steps"]])
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
    blocks = ([("login", steps["login"]["steps"], None)] if steps.get("login") and not is_manual(steps) else []) + [
        (sid, sc.get("steps", []), sc) for sid, sc in sorted(steps["scenes"].items()) if not only or sid == only]
    visible = None
    with sync_playwright() as p:
        if is_manual(steps):
            ctx = launch_profile_sync(p, steps)
            browser = ctx
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                manual_login_sync(page, steps, base)
            except PWError:
                ctx.close()
                emit("capture", ok=False, user_action=True, message=login_timeout_msg(steps))
            moved = hidden_session_sync(p, ctx, page, steps, base)
            if moved:  # rehearse exactly where the recording will happen; the person's window shows a calm tint
                guide_sync(page, "tint", "Rehearsing in the background", "Checking every step before the real recording")
                visible, browser = ctx, moved[0]
                page = moved[2]
        else:
            browser = p.chromium.launch()
            page = browser.new_context(**ctx_args(steps)).new_page()
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
        if visible:
            visible.close()
    sheet = contact_sheet(d)
    res = {"scenes": [r for r in results if r["scene"] != "login"], "failures": failures, "skipped": skipped,
           "outputs": [str(sheet)] if sheet else []}
    (d / "result.json").write_text(json.dumps(res, indent=2))
    if failures:
        emit("capture", ok=False, user_action=True, message=f"{len(failures)} scene(s) failed the dry run", **res)
    emit("capture", message=f"dry run passed: {len(res['scenes'])} scene(s)", **res)


# ---------- record (async, so screencast frames keep flowing while we wait for a word)

def login_timeout_msg(steps):
    return (f"Nobody finished logging in within {steps['login'].get('timeout_s', 600)} s. Ask the person to log in "
            "in the window, then run this again; or record the logged-in scenes as clips.")


def launch_profile_sync(p, steps):
    kw = dict(user_data_dir=profile_dir(steps), headless=not headed(), **ctx_args(steps), **PROFILE_ARGS)
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kw)  # real Chrome: Google sign-in works more often
    except Exception:
        return p.chromium.launch_persistent_context(**kw)


async def launch_profile_async(p, steps):
    kw = dict(user_data_dir=profile_dir(steps), headless=not headed(), **ctx_args(steps), **PROFILE_ARGS)
    try:
        return await p.chromium.launch_persistent_context(channel="chrome", **kw)
    except Exception:
        return await p.chromium.launch_persistent_context(**kw)


def guide_sync(page, fn, *args):
    """Show or clear the in-browser guide (templates/guide.js). A page that's mid-navigation just skips a beat."""
    try:
        page.evaluate(GUIDE_JS.read_text(encoding="utf-8"))
        return page.evaluate("([f, a]) => window.__unveo[f](...a)", [fn, list(args)])
    except Exception:
        return None


async def guide_async(page, fn, *args):
    try:
        await page.evaluate(GUIDE_JS.read_text(encoding="utf-8"))
        return await page.evaluate("([f, a]) => window.__unveo[f](...a)", [fn, list(args)])
    except Exception:
        return None


def login_point(page, steps, base):
    """Where the dotted pointer goes: login.point_at, else the page's own sign-in button (None); nothing off the app."""
    if not same_origin(page.url, base):
        return False
    at = steps["login"].get("point_at")
    if not at:
        return None
    try:
        return locate(page, at).first.bounding_box(timeout=300) or None
    except Exception:
        return None


async def alogin_point(page, steps, base):
    if not same_origin(page.url, base):
        return False
    at = steps["login"].get("point_at")
    if not at:
        return None
    try:
        return await locate(page, at).first.bounding_box(timeout=300) or None
    except Exception:
        return None


def manual_login_sync(page, steps, base, on_wait=None):
    page.goto(urljoin(base, steps["login"]["start"]), wait_until="load")
    try:  # already logged in (the profile remembers)?
        perform(page, {**login_wait_step(steps), "timeout_ms": 2500}, base, os.environ, False)
        return
    except Exception:
        pass
    log(LOGIN_HELP)
    deadline = time.time() + steps["login"].get("timeout_s", 600)
    while True:  # re-draw the guide every second: the person may navigate, or the button may move
        guide_sync(page, "login", LOGIN_BAR, login_point(page, steps, base))
        if on_wait:
            on_wait()
        try:
            perform(page, {**login_wait_step(steps), "timeout_ms": 1000}, base, os.environ, False)
            break
        except Exception:
            if time.time() > deadline:
                guide_sync(page, "clear")
                raise
    guide_sync(page, "clear")


async def manual_login_async(page, steps, base):
    await page.goto(urljoin(base, steps["login"]["start"]), wait_until="load")
    try:
        await aperform(page, {**login_wait_step(steps), "timeout_ms": 2500}, base, os.environ)
        return
    except Exception:
        pass
    log(LOGIN_HELP)
    deadline = time.time() + steps["login"].get("timeout_s", 600)
    while True:
        await guide_async(page, "login", LOGIN_BAR, await alogin_point(page, steps, base))
        try:
            await aperform(page, {**login_wait_step(steps), "timeout_ms": 1000}, base, os.environ)
            break
        except Exception:
            if time.time() > deadline:
                await guide_async(page, "clear")
                raise
    await guide_async(page, "clear")


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def schedule(steps, words, lead_s):
    """Seconds into the scene when each step should start: just before its 'say' word. None = right after the previous step."""
    at, ptr = [], 0
    for st in steps:
        say = [norm(x) for x in str(st.get("say", "")).split() if norm(x)]
        hit = None
        if say:
            for i in range(ptr, len(words)):
                if norm(words[i]["w"]).startswith(say[0]):
                    hit, ptr = i, i + 1
                    break
        at.append(max(0.0, lead_s + words[hit]["t0"] - EARLY_S) if hit is not None else None)
    return at


async def glide(page, loc):
    await loc.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT_MS)
    box = await loc.bounding_box()
    if box:
        await page.evaluate("([x, y, ms]) => window.__unveoCursor && window.__unveoCursor.moveTo(x, y, ms)",
                            [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, GLIDE_MS])


async def aperform(page, st, base, env):
    to = st.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    loc = locate(page, st["target"]).first if st.get("target") else None
    do = st["do"]
    if do in ("click", "submit", "hover", "type", "select"):
        await glide(page, loc)
    if do == "goto":
        await page.goto(urljoin(base, st["url"]), wait_until="load", timeout=to)
    elif do in ("click", "submit"):
        await page.evaluate("() => window.__unveoCursor && window.__unveoCursor.click()")
        await loc.click(timeout=to)
    elif do == "type":
        await loc.click(timeout=to)
        await loc.fill("", timeout=to)
        if st.get("secret"):
            await loc.evaluate("e => { e.style.filter = 'blur(7px)'; }")  # never show a password on screen
        await page.keyboard.type(substitute(st["text"], env), delay=st.get("delay_ms", 55))
    elif do == "select":
        await loc.select_option(**({"value": st["value"]} if st.get("value") else {"label": st["label"]}), timeout=to)
    elif do == "press":
        await (loc.press(st["key"], timeout=to) if loc else page.keyboard.press(st["key"]))
    elif do == "scroll":
        if loc:
            await loc.evaluate("e => e.scrollIntoView({behavior: 'smooth', block: 'center'})")
            await page.wait_for_timeout(st.get("ms", 900))
        else:
            n = max(1, st.get("ms", 900) // 30)
            for _ in range(n):
                await page.mouse.wheel(0, st["by"] / n)
                await page.wait_for_timeout(30)
    elif do == "hover":
        await loc.hover(timeout=to)
    elif do == "wait":
        w = st["for"]
        if w == "network-idle":
            await page.wait_for_load_state("networkidle", timeout=to)
        elif w == "selector":
            await loc.wait_for(state="visible", timeout=to)
        elif w == "url":
            await page.wait_for_url(lambda u: st["value"] in u, timeout=to)
        elif w == "text":
            await page.get_by_text(st["value"]).first.wait_for(state="visible", timeout=to)
        else:
            await page.wait_for_timeout(st["value"])
    elif do == "pause":
        await page.wait_for_timeout(st["ms"])


def encode(frames, t_start, t_end, path, zooms=(), size=(1920, 1080), light=False):
    """Timestamped JPEG frames -> constant 30 fps h264 (1920x1080, or a phone's 430x932). Each frame shows until the
    next one arrives; zooms crop in smoothly (zoom_crop), or with light=True dim around the target instead (spotlight)."""
    OW, OH = size
    import io
    from bisect import bisect_right
    from PIL import Image
    times = [max(0.0, ts - t_start) for ts, _ in frames]
    n = max(1, round((t_end - t_start) * 30))
    enc = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", "30",
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(path)],
                           stdin=subprocess.PIPE)
    cache_src, cache_key, cache_out = None, None, None
    try:
        for i in range(n):
            t = i / 30
            idx = max(0, bisect_right(times, t) - 1)
            if cache_src is None or cache_src[0] != idx:
                cache_src = (idx, Image.open(io.BytesIO(base64.b64decode(frames[idx][1]))).convert("RGB"))
            img = cache_src[1]
            if light:
                k, z = zoom_k(t, zooms)
                crop = (0, 0, *img.size, round(k, 2))
            else:
                crop = zoom_crop(t, zooms, *img.size)
            if (idx, crop) != cache_key:
                part = img.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3]))
                if light and z:
                    part = spotlight(part, k, z["box"])
                scale = min(OW / part.width, OH / part.height)
                fitted = part.resize((round(part.width * scale), round(part.height * scale)), Image.LANCZOS)
                if scale > 1.05:  # zoomed in: a light sharpen keeps text crisp
                    from PIL import ImageFilter
                    fitted = fitted.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
                canvas = Image.new("RGB", (OW, OH))
                canvas.paste(fitted, ((OW - fitted.width) // 2, (OH - fitted.height) // 2))
                cache_key, cache_out = (idx, crop), canvas.tobytes()
            enc.stdin.write(cache_out)
    finally:
        enc.stdin.close()
        enc.wait()
    if enc.returncode:
        raise RuntimeError(f"ffmpeg failed encoding {path}")


async def dismiss_banners(page):
    for name in ("Accept", "Accept all", "Got it", "I agree"):
        try:
            await page.get_by_role("button", name=name, exact=True).click(timeout=300)
        except Exception:
            pass


async def record_scenes(out, only):
    from playwright.async_api import async_playwright, Error as PWError
    o = Path(out)
    steps = load_steps(out)
    try:
        timeline = read_json(o / "timeline.json")
        voice = {c["scene"]: c for c in read_json(o / "voice" / "voice.json")["clips"]}
    except (OSError, ValueError) as e:
        emit("capture", ok=False, user_action=True, message=f"run voice.py and plan_timeline.py first ({e})")
    scenes = [s for s in timeline["scenes"] if s["visual"] == "capture" and (not only or s["id"] == only)]
    missing = [s["id"] for s in scenes if s["id"] not in steps["scenes"]]
    if missing:
        emit("capture", ok=False, user_action=True, message=f"steps.json has no entry for {missing}")
    env_missing = [n for n in env_names(steps) if not os.environ.get(n)]
    if env_missing:
        emit("capture", ok=False, user_action=True, missing_env=env_missing,
             message=f"Set {' and '.join(env_missing)} in your terminal first, then run again.")
    base, results, failures = steps["base_url"], [], []
    visible, hidden_browser, recorded_in = None, None, "hidden"
    async with async_playwright() as p:
        if is_manual(steps):
            ctx = browser = await launch_profile_async(p, steps)
            await ctx.add_init_script(path=str(CURSOR_JS))
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            try:
                await manual_login_async(page, steps, base)
            except PWError:
                await ctx.close()
                emit("capture", ok=False, user_action=True, message=login_timeout_msg(steps))
            visible = page  # the person's window: from now on it only shows a calm tint
            moved = await hidden_session(p, ctx, page, steps, base)
            if moved:
                hidden_browser, ctx, page = moved
            else:
                recorded_in = "window"
            await guide_async(visible, "tint", "Recording in the background" if moved else "Recording in this window",
                              "Getting ready…" if moved else "Please don't touch the mouse or keyboard until it's done.")
        else:
            browser = await p.chromium.launch()
            ctx = await browser.new_context(**ctx_args(steps))
            await ctx.add_init_script(path=str(CURSOR_JS))
            page = await ctx.new_page()
            if steps.get("login"):
                for st in steps["login"]["steps"]:
                    await aperform(page, st, base, os.environ)
        first = True
        for k, scene in enumerate(scenes, 1):
            sid, sc = scene["id"], steps["scenes"][scene["id"]]
            words = (voice.get(sid) or {}).get("words", [])
            display = sc.get("display")
            phone = display == "phone"
            await page.set_viewport_size({"width": 430, "height": 932} if phone else ctx_args(steps)["viewport"])
            try:  # get to the starting page before the camera rolls
                if sc.get("start") and page.url.rstrip("/") != urljoin(base, sc["start"]["url"]).rstrip("/"):
                    await aperform(page, sc["start"], base, os.environ)
                elif page.url == "about:blank":
                    await page.goto(base, wait_until="load")
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except PWError:
                    pass
                if first:
                    await dismiss_banners(page)
                    first = False
            except PWError as e:
                failures.append({"scene": sid, "step": "start", "error": str(e).splitlines()[0]})
                continue
            title = None
            if visible is not None and recorded_in == "hidden":  # their window just says how far along it is
                await guide_async(visible, "tint", "Recording in the background", f"Scene {k} of {len(scenes)} · you can leave this window")
            elif visible is not None:  # recording in their window: lift the tint just before the camera rolls
                await guide_async(page, "tint", "Recording in this window", f"Scene {k} of {len(scenes)} · hands off for a moment")
                await asyncio.sleep(0.3)
                await guide_async(page, "clear")
                title = await page.title()
                await page.evaluate("t => { document.title = t; }", f"● REC {sid} · unveo")
                await page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            frames = []
            cdp = await ctx.new_cdp_session(page)

            def on_frame(f, cdp=cdp, frames=frames):
                frames.append((f["metadata"]["timestamp"], f["data"]))
                ack = asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]}))
                ack.add_done_callback(lambda t: t.exception())  # a late ack after the page closed is harmless
            cdp.on("Page.screencastFrame", on_frame)
            await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})
            t0, wall0 = time.monotonic(), time.time()
            at, actions, err, last_end = schedule(sc.get("steps", []), words, scene.get("lead_s", 0.3)), [], None, 0.0
            zooms = []
            for i, st in enumerate(sc.get("steps", [])):
                f = flag(st)
                if f == "payment" or (f == "destructive" and not st.get("approved")):
                    continue
                want = at[i] if at[i] is not None else last_end + (MIN_GAP_S if actions else 0)
                await asyncio.sleep(max(0.0, want - (time.monotonic() - t0)))
                actions.append({"step": i, "at_s": round(time.monotonic() - t0, 2), "do": st["do"]})
                try:
                    await aperform(page, st, base, os.environ)
                    if not same_origin(page.url, base):
                        raise RuntimeError(f"left the app: went outside {base} to {page.url}")
                    if st.get("zoom"):
                        z = st["zoom"] if isinstance(st["zoom"], dict) else {}
                        box = await locate(page, z.get("target") or st["target"]).first.bounding_box()  # frame a whole card, act on its button
                        if box:
                            zooms.append({"t_s": round(time.monotonic() - t0, 2), "scale": float(z.get("scale", ZOOM_SCALE)),
                                          "hold_s": float(z.get("hold_s", ZOOM_HOLD_S)),
                                          "box": [round(box[k]) for k in ("x", "y", "width", "height")]})  # frames are CSS-pixel sized
                except (PWError, RuntimeError, KeyError) as e:
                    err = {"scene": sid, "step": i, "error": (str(e).splitlines() or [repr(e)])[0][:300]}
                    break
                last_end = time.monotonic() - t0
            elapsed = time.monotonic() - t0
            need = round(last_end + SETTLE_S, 2) if actions else 0.0
            await asyncio.sleep(max(0.0, max(scene["dur_s"], need) - elapsed))
            await page.mouse.move(1, 1)  # nudge a repaint so the hold has a fresh frame
            await asyncio.sleep(0.05)
            await cdp.send("Page.stopScreencast")
            if title is not None:
                try:
                    await page.evaluate("t => { document.title = t; }", title)
                except PWError:
                    pass
            wall_end = wall0 + max(scene["dur_s"], time.monotonic() - t0)
            await cdp.detach()
            if not frames:
                frames = [(wall0, base64.b64encode(await page.screenshot(type="jpeg", quality=90)).decode())]
            path = o / "capture" / f"{sid}.mp4"
            encode(sorted(frames), wall0, wall_end, path, zooms, size=(430, 932) if phone else (1920, 1080), light=display == "spotlight")
            if err:
                failures.append(err)
            results.append({"scene": sid, "file": str(path), "target_s": scene["dur_s"],
                            "recorded_s": round(wall_end - wall0, 2), "over_s": round(max(0.0, elapsed - scene["dur_s"]), 2),
                            "need_s": need, "actions": actions, "zooms": zooms, "ok": err is None})
        if visible is not None:
            await guide_async(visible, "tint", "Done. Recording finished.", "unveo closes this window by itself.", True)
            await asyncio.sleep(1.5)
        if hidden_browser:
            await hidden_browser.close()
        await browser.close()
    res = {"scenes": results, "failures": failures, "outputs": [r["file"] for r in results], "recorded_in": recorded_in}
    rec = o / "capture" / "record.json"  # how long each recording needs; plan_timeline makes room for it
    known = json.loads(rec.read_text()) if rec.exists() else {}
    known.update({r["scene"]: {"need_s": r["need_s"], "recorded_s": r["recorded_s"]} for r in results})
    rec.write_text(json.dumps(known, indent=1))
    longer = [r["scene"] for r in results if r["need_s"] > r["target_s"] + 0.05]
    if longer:
        res["settle"] = longer
        res["next"] = "run plan_timeline.py again: it lengthens " + ", ".join(longer) + " so the cut doesn't land on a click"
    if failures:
        emit("capture", ok=False, user_action=True, message=f"{len(failures)} scene(s) failed while recording", **res)
    over = [r["scene"] for r in results if r["over_s"] > 1.5]
    emit("capture", message=f"recorded {len(results)} scene(s)" + (f"; {over} ran long" if over else ""), **res)


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
    for name in ("check", "dry-run", "record"):
        sp = sub.add_parser(name)
        sp.add_argument("--scene")
    for sp in sub.choices.values():
        sp.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    if a.cmd == "probe":
        probe(a.url, a.out)
    elif a.cmd == "check":
        check_cmd(a.out)
    elif a.cmd == "record":
        asyncio.run(record_scenes(a.out, a.scene))
    else:
        dry_run(a.out, a.scene)


if __name__ == "__main__":
    main()
