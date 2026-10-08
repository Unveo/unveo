"""Record the real web app (docs/10).

  capture.py probe --url <url> [--out unveo-out/.work]   open the app once: status, title, login wall, screenshot
  capture.py check   [--out unveo-out/.work]             validate capture/steps.json, flag risky steps, list the plan in plain words
  capture.py dry-run [--out unveo-out/.work]   run every scene fast, no recording; screenshots + failure details
  capture.py record  [--out unveo-out/.work]   one take: every scene in order, one session, natural pace, no voice
                                                needed -> capture/sNN.mp4 + capture/record.json (stitch.py retimes them)
"""
import argparse, asyncio, base64, difflib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from common import INTERMEDIATE_CRF, emit, ffmpeg_exe, log, out_dir, out_size, read_json  # noqa: E402

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
        b = p.chromium.launch(args=launch_args(steps))
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
        b = await p.chromium.launch(args=launch_args(steps))
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
async def offscreen_page(ctx, vpage, steps, base):
    """A second window in the person's own browser, moved off the screen: it shares their login completely (only
    sessionStorage is copied), so it works where a hidden browser was refused. None if it can't film there."""
    pg = None
    try:
        origin = await vpage.evaluate("location.origin")
        pairs = await vpage.evaluate("() => Object.entries(sessionStorage)")
        await ctx.add_init_script(script=session_script(origin, pairs))
        cdp = await ctx.new_cdp_session(vpage)
        async with ctx.expect_page() as info:
            await cdp.send("Target.createTarget", {"url": "about:blank", "newWindow": True, "background": True})
        pg = await info.value
        s = await ctx.new_cdp_session(pg)
        try:  # off the screen; a headless browser has no windows to move
            w = await s.send("Browser.getWindowForTarget")
            await s.send("Browser.setWindowBounds", {"windowId": w["windowId"], "bounds": {"left": -6000, "top": 0}})
        except Exception:
            pass
        await pg.set_viewport_size(ctx_args(steps)["viewport"])
        await pg.goto(urljoin(base, steps["login"]["start"]), wait_until="load")
        await aperform(pg, {**login_wait_step(steps), "timeout_ms": int(HIDDEN_CHECK_S * 1000)}, base, os.environ)
        got = []

        def on_frame(f):
            got.append(1)
            asyncio.ensure_future(s.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})).add_done_callback(lambda t: t.exception())
        s.on("Page.screencastFrame", on_frame)
        await s.send("Page.startScreencast", {"format": "jpeg", "quality": 30, "everyNthFrame": 1})
        for i in range(30):  # up to 3 s for a first frame: an offscreen window that doesn't paint is no use
            await pg.mouse.move(10 + i, 10)
            await asyncio.sleep(0.1)
            if got:
                break
        await s.send("Page.stopScreencast")
        await s.detach()
        if not got:
            raise RuntimeError("the offscreen window sends no picture")
        return pg
    except Exception as e:
        log(f"no offscreen window either ({str(e).splitlines()[0][:120]}); recording in the visible window")
        if pg:
            try:
                await pg.close()
            except Exception:
                pass
        return None


async def keep_tint(page, state):
    """Keep the person's window tinted for as long as it's open: redraw it every second, so a reload, a navigation or
    the app re-rendering never leaves it bare. state[0] = (title, sub, done)."""
    while True:
        if state[0]:
            await guide_async(page, "tint", *state[0])
        await asyncio.sleep(1)


EARLY_S, MIN_GAP_S, GLIDE_MS = 0.3, 0.5, 550
LEAD_S = 0.6     # the take's natural pace: a beat before a scene's first action, then MIN_GAP_S between actions
SETTLE_S = 0.8   # after the last action the page holds this long, so a cut never lands on a click
MAX_SPEED = 2.5  # stitch.py may play a recording up to this much faster to meet its voice


ZOOM_EASE_S, ZOOM_HOLD_S, ZOOM_SCALE = 0.6, 2.0, 1.6


def has_zoom(steps):
    return any(st.get("zoom") for sc in (steps.get("scenes") or {}).values() for st in sc.get("steps", []))


def pixel_scale(steps):
    """Device pixels per CSS pixel: viewport.zoom times the output scale (2K = 4/3)."""
    return float((steps.get("viewport") or {}).get("zoom", 1.0)) * steps.get("_scale", 1.0)


def ctx_args(steps, hi_res=False):
    """The page always lays out at 1920x1080 CSS (viewport.zoom > 1 enlarges the UI with the real layout).
    For 2K the page renders at 4/3 pixel density, so it's captured natively at 2560x1440. The screencast only
    delivers device pixels when Chrome is started with --force-device-scale-factor (launch_args); the context's
    own device_scale_factor alone still gives CSS-sized frames (measured 7 Oct 2026). CSS zoom is not used."""
    z = float((steps.get("viewport") or {}).get("zoom", 1.0))
    return {"viewport": {"width": round(1920 / z), "height": round(1080 / z)}, "device_scale_factor": pixel_scale(steps)}


def launch_args(steps):
    d = pixel_scale(steps)
    return [f"--force-device-scale-factor={d:.4f}"] if abs(d - 1) > 1e-3 else []


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


def frame_box(box, sx, sy):
    """A CSS-pixel box in frame pixels: the screencast frame isn't always CSS-sized (a resized window, a smaller viewport)."""
    bx, by, bw, bh = box
    return bx * sx, by * sy, bw * sx, bh * sy


def zoom_crop(t, zooms, W, H, sx=1.0, sy=1.0):
    """The part of a W x H frame to show at time t: eases in on the zoom's box, holds, eases back out (docs/15 A9)."""
    k, z = zoom_k(t, zooms)
    if z:
        s = 1 + (z["scale"] - 1) * k
        w, h = round(W / s), round(H / s)
        bx, by, bw, bh = frame_box(z["box"], sx, sy)
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
    e = []
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


PROFILE_ARGS = {"ignore_default_args": ["--enable-automation"],
                "args": ["--disable-blink-features=AutomationControlled",  # an offscreen window must keep painting:
                         "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
                         "--disable-background-timer-throttling"]}


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


def frame_warnings(steps):
    """An older steps.json may give a scene its own frame; it's ignored (looks.display_for), so it's only a warning."""
    import looks
    return [f"{sid}: its display '{sc['display']}' is ignored; the frame is set once for the whole video in film/design.json "
            f"(\"display\"), and a scene may only use {' or '.join(looks.SCENE_DISPLAYS)}"
            for sid, sc in sorted((steps.get("scenes") or {}).items()) if sc.get("display") and sc["display"] not in looks.SCENE_DISPLAYS]


def check_cmd(out):
    steps = load_steps(out)
    plan = {}
    if steps.get("login"):
        plan["login"] = ([login_plan(steps["login"])] if is_manual(steps) else [plan_line(s) for s in steps["login"]["steps"]])
    for sid, sc in sorted(steps["scenes"].items()):
        plan[sid] = [plan_line(s) for s in ([sc["start"]] if sc.get("start") else []) + sc.get("steps", [])]
    emit("capture", plan=plan, warnings=frame_warnings(steps), message="steps.json OK")


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


def dry_run(out):
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
        (sid, sc.get("steps", []), sc) for sid, sc in sorted(steps["scenes"].items())]
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
    kw["args"] = PROFILE_ARGS["args"] + launch_args(steps)
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kw)  # real Chrome: Google sign-in works more often
    except Exception:
        return p.chromium.launch_persistent_context(**kw)


async def launch_profile_async(p, steps):
    kw = dict(user_data_dir=profile_dir(steps), headless=not headed(), **ctx_args(steps), **PROFILE_ARGS)
    kw["args"] = PROFILE_ARGS["args"] + launch_args(steps)
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
    times = [max(0.0, f[0] - t_start) for f in frames]
    n = max(1, round((t_end - t_start) * 30))
    enc = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", "30",
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(INTERMEDIATE_CRF), "-pix_fmt", "yuv420p", "-an", str(path)],
                           stdin=subprocess.PIPE)
    cache_src, cache_key, cache_out = None, None, None
    try:
        for i in range(n):
            t = i / 30
            idx = max(0, bisect_right(times, t) - 1)
            if cache_src is None or cache_src[0] != idx:
                cache_src = (idx, Image.open(io.BytesIO(base64.b64decode(frames[idx][1]))).convert("RGB"))
            img = cache_src[1]
            css = frames[idx][2:4]  # the CSS size this frame covers (screencast metadata); zoom boxes are in CSS pixels
            sx, sy = (img.width / css[0], img.height / css[1]) if len(css) == 2 and all(css) else (1.0, 1.0)
            if light:
                k, z = zoom_k(t, zooms)
                crop = (0, 0, *img.size, round(k, 2))
            else:
                crop = zoom_crop(t, zooms, *img.size, sx, sy)
            if (idx, crop) != cache_key:
                part = img.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3]))
                if light and z:
                    part = spotlight(part, k, frame_box(z["box"], sx, sy))
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


async def record_scenes(out):
    """One take: every capture scene in order, in one browser session, under one continuous screencast, at a natural
    pace (no voice needed). Each scene is cut out of the take as capture/sNN.mp4 at its own length; stitch.py ingest
    later retimes it to the voice. A failing scene ends the take (later scenes depend on its page state)."""
    from playwright.async_api import async_playwright, Error as PWError
    o = Path(out)
    steps = load_steps(out)
    W, H = out_size(o)
    steps["_scale"] = W / 1920  # record at the output's pixel density: 2K is captured natively
    even = lambda v: int(round(v / 2) * 2)
    order = sorted(steps["scenes"])
    env_missing = [n for n in env_names(steps) if not os.environ.get(n)]
    if env_missing:
        emit("capture", ok=False, user_action=True, missing_env=env_missing,
             message=f"Set {' and '.join(env_missing)} in your terminal first, then run again.")
    base, results, failures, skipped = steps["base_url"], [], [], []
    shots = o / "capture" / "take"
    shots.mkdir(parents=True, exist_ok=True)
    for old in shots.glob("*.png"):
        old.unlink()
    visible, hidden_browser, recorded_in, keeper, tint = None, None, "hidden", None, [None]
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
            visible = page  # the person's window: from now on it shows the yellow "Recording" tint until it closes
            moved = await hidden_session(p, ctx, page, steps, base)
            if moved:
                hidden_browser, ctx, page = moved
            else:
                off = await offscreen_page(ctx, visible, steps, base)
                page, recorded_in = (off, "offscreen") if off else (visible, "window")
            if recorded_in != "window":
                tint[0] = ("unveo is recording", "Getting ready… please leave this window open", False)
                keeper = asyncio.ensure_future(keep_tint(visible, tint))
            else:
                await guide_async(visible, "tint", "Recording in this window", "Please don't touch the mouse or keyboard until it's done.")
        else:
            browser = await p.chromium.launch(args=launch_args(steps))
            ctx = await browser.new_context(**ctx_args(steps))
            await ctx.add_init_script(path=str(CURSOR_JS))
            page = await ctx.new_page()
            if steps.get("login"):
                for st in steps["login"]["steps"]:
                    await aperform(page, st, base, os.environ)
        title = None
        if recorded_in == "window":  # the camera sees this window: lift the tint once, for the whole take
            await asyncio.sleep(0.3)
            await guide_async(page, "clear")
            title = await page.title()
            await page.evaluate("t => { document.title = t; }", "● REC · unveo")
        cdp = await ctx.new_cdp_session(page)
        bucket, last = [None], [None]  # frames go to the scene that's rolling; between scenes they're dropped

        def on_frame(f):
            md = f["metadata"]
            fr = (md["timestamp"], f["data"], md.get("deviceWidth"), md.get("deviceHeight"))
            last[0] = fr
            if bucket[0] is not None:
                bucket[0].append(fr)
            ack = asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]}))
            ack.add_done_callback(lambda t: t.exception())  # a late ack after the page closed is harmless
        cdp.on("Page.screencastFrame", on_frame)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 100, "maxWidth": 3840, "maxHeight": 2160, "everyNthFrame": 1})
        first = True
        for k, sid in enumerate(order, 1):
            sc = steps["scenes"][sid]
            display = sc.get("display")
            phone = display == "phone"
            await page.set_viewport_size({"width": 430, "height": 932} if phone else ctx_args(steps)["viewport"])
            try:  # get to the starting page between scenes; that part of the take is dropped
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
                break
            if keeper:  # their window just says how far along it is
                tint[0] = ("unveo is recording", f"Scene {k} of {len(order)} · please leave this window open", False)
                await guide_async(visible, "tint", *tint[0])
            await page.mouse.move(2, 2)  # nudge a repaint so the scene opens on a fresh frame
            await page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            frames = []
            t0, wall0 = time.monotonic(), time.time()
            if last[0]:
                frames.append((wall0, *last[0][1:]))  # a still page sends no frames: open on what's showing
            bucket[0] = frames
            actions, zooms, err, last_end = [], [], None, 0.0
            for i, st in enumerate(sc.get("steps", [])):
                f = flag(st)
                if f == "payment" or (f == "destructive" and not st.get("approved")):
                    skipped.append({"scene": sid, "step": i, "flag": f, "what": describe(st)})
                    continue
                await asyncio.sleep(max(0.0, last_end + (MIN_GAP_S if actions else LEAD_S) - (time.monotonic() - t0)))
                actions.append({"step": i, "at_s": round(time.monotonic() - t0, 2), "do": st["do"], "say": st.get("say", "")})
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
                    wanted = target_text(st.get("target"))
                    shot = shots / f"{sid}-fail.png"
                    try:
                        await page.screenshot(path=str(shot))
                        near = difflib.get_close_matches(wanted, list(dict.fromkeys(await page.evaluate(CANDIDATES_JS))), n=5, cutoff=0)
                    except PWError:
                        near = []
                    err = {"scene": sid, "step": i, "error": (str(e).splitlines() or [repr(e)])[0][:300],
                           "closest": near, "screenshot": str(shot)}
                    break
                last_end = time.monotonic() - t0
            zoom_end = max((z["t_s"] + 2 * ZOOM_EASE_S + z["hold_s"] for z in zooms), default=0.0)
            raw = max(last_end + SETTLE_S, zoom_end, 1.0)  # the scene's natural length: settle after the last action
            await asyncio.sleep(max(0.0, raw - (time.monotonic() - t0)))
            await page.mouse.move(1, 1)  # a fresh frame for the end
            await asyncio.sleep(0.05)
            bucket[0] = None
            wall_end = wall0 + raw
            if not err:
                await page.screenshot(path=str(shots / f"{sid}.png"))
            path = o / "capture" / f"{sid}.mp4"
            size = (even(430 * steps["_scale"]), even(932 * steps["_scale"])) if phone else (W, H)
            encode(sorted(frames), wall0, wall_end, path, zooms, size=size, light=display == "spotlight")
            area = next(([f[2], f[3]] for f in frames if len(f) == 4 and f[2] and f[3]), None)  # CSS size the camera saw
            results.append({"scene": sid, "file": str(path), "recorded_s": round(raw, 2), "need_s": round(raw / MAX_SPEED, 2),
                            "actions": actions, "zooms": zooms, "area": area, "ok": err is None})
            if err:
                failures.append(err)
                break  # the scenes after it start from this page state, so the take stops here
        await cdp.send("Page.stopScreencast")
        await cdp.detach()
        if title is not None:
            try:
                await page.evaluate("t => { document.title = t; }", title)
            except PWError:
                pass
        if visible is not None:
            tint[0] = ("Done. Recording finished.", "unveo closes this window by itself.", True)
            await guide_async(visible, "tint", *tint[0])
            await asyncio.sleep(1.5)
        if keeper:
            keeper.cancel()
        if hidden_browser:
            await hidden_browser.close()
        await browser.close()
    sheet = contact_sheet(shots)
    res = {"scenes": results, "failures": failures, "skipped": skipped, "recorded_in": recorded_in,
           "outputs": [r["file"] for r in results] + ([str(sheet)] if sheet else [])}
    # the take, for stitch.py: each scene's natural length and when its actions happened
    write_take(o, {r["scene"]: {k: r[k] for k in ("recorded_s", "need_s", "actions", "zooms")} for r in results})
    if failures:
        done = [r["scene"] for r in results if r["ok"]]
        emit("capture", ok=False, user_action=True, message=f"{failures[0]['scene']} failed, so the take stopped there "
             f"(recorded fine: {done or 'none'}). Fix it from 'closest' and the screenshot, then record again.", **res)
    want = {r["scene"]: 430 / 932 if (steps["scenes"][r["scene"]].get("display") == "phone") else 16 / 9 for r in results}
    boxed = [r["scene"] for r in results if r["area"] and abs(r["area"][0] / r["area"][1] / want[r["scene"]] - 1) > 0.02]
    if boxed:  # e.g. the person's window was resized or is smaller than the viewport: the video gets black bars
        res["letterboxed"] = boxed
        res["fix"] = ("the browser showed a non-16:9 area for " + ", ".join(boxed) + " (see each scene's area), so those videos "
                      "have black bars; keep the recording window unresized (or use a bigger screen) and record again")
    emit("capture", message=f"recorded {len(results)} scene(s) in one take ({sum(r['recorded_s'] for r in results):.0f} s)", **res)


def write_take(o, scenes):
    (o / "capture" / "record.json").write_text(json.dumps(scenes, indent=1))


def read_take(o):
    f = Path(o) / "capture" / "record.json"
    return json.loads(f.read_text()) if f.exists() else {}


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
        sub.add_parser(name)
    for sp in sub.choices.values():
        sp.add_argument("--out", default="unveo-out/.work")
    a = ap.parse_args()
    if a.cmd == "probe":
        probe(a.url, a.out)
    elif a.cmd == "check":
        check_cmd(a.out)
    elif a.cmd == "record":
        asyncio.run(record_scenes(a.out))
    else:
        dry_run(a.out)


if __name__ == "__main__":
    main()
