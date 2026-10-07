"""Optional: record the narration in your own voice (docs/15 B6). Never required.

  studio.py serve [--out unveo-out] [--port 0] [--no-open] [--timeout 3600]

Opens a local teleprompter page: the line to read is highlighted; Record, Play it back, Re-record if
needed, then Approve. The word being said lights up (Chrome's speech recognition) and a pace guide moves at the
speed chosen in the brief. Approved takes are saved to voice/own/<scene>.webm with the time each word was heard
(<scene>.words.json), so the video can follow the real voice; Finish ends the session.
Then run `voice.py --provider own` to use them. The audio stays on this computer; in Chrome the live
highlight uses the browser's built-in speech recognition, which sends audio to Google while you record.
"""
import argparse, http.server, json, re, socketserver, sys, threading, webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit, out_dir  # noqa: E402
import script as scriptmod  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
PAGE = TEMPLATES / "studio" / "index.html"
FILES = {"/logo.png": TEMPLATES / "brand" / "logo.png", "/favicon.png": TEMPLATES / "brand" / "favicon.png"}
EXTS = (".webm", ".wav", ".m4a", ".mp3", ".ogg", ".mp4")


def lines(o):
    """Each line to read, with the pace to read it at (the speed chosen in the brief) and how long that takes."""
    scenes = [s for s in scriptmod.parse((o / "script.md").read_text(encoding="utf-8")) if s["narration"]]
    brief = json.loads((o / "brief.json").read_text(encoding="utf-8")) if (o / "brief.json").exists() else {}
    wps = scriptmod.RATE.get(brief.get("language", "en"), 2.2) * scriptmod.rate_factor((brief.get("voice") or {}).get("rate"))
    own = o / "voice" / "own"
    out = []
    for s in scenes:
        text = scriptmod.spoken(s["narration"])
        out.append({"id": s["id"], "segment": s["segment"], "text": text, "lang": brief.get("language", "en"), "wps": round(wps, 3),
                    "target_s": round(len(text.split()) / wps, 2),
                    "approved": any((own / f"{s['id']}{e}").exists() for e in EXTS)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["serve"])
    ap.add_argument("--out", default="unveo-out")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    o = out_dir(a.out)
    own = o / "voice" / "own"
    own.mkdir(parents=True, exist_ok=True)
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/lines":
                self.send(200, lines(o))
            elif self.path in FILES and FILES[self.path].exists():
                self.send(200, FILES[self.path].read_bytes(), "image/png")
            else:
                self.send(404, {"ok": False})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            m = re.fullmatch(r"/take/(s\d{2})", self.path)
            if m and m.group(1) in {l["id"] for l in lines(o)}:  # only real scene ids: no path tricks
                for e in EXTS:
                    (own / f"{m.group(1)}{e}").unlink(missing_ok=True)
                (own / f"{m.group(1)}.webm").write_bytes(body)
                self.send(200, {"ok": True})
            elif (w := re.fullmatch(r"/words/(s\d{2})", self.path)) and w.group(1) in {l["id"] for l in lines(o)}:
                try:
                    words = [{"w": str(x["w"]), "t": None if x.get("t") is None else float(x["t"])} for x in json.loads(body)["words"]]
                except (ValueError, KeyError, TypeError):
                    return self.send(400, {"ok": False})
                (own / f"{w.group(1)}.words.json").write_text(json.dumps({"words": words}))
                self.send(200, {"ok": True})
            elif self.path == "/finish":
                self.send(200, {"ok": True})
                done.set()
            else:
                self.send(404, {"ok": False})

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", a.port), Handler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    (o / "voice" / "studio.url").write_text(url)
    if not a.no_open:
        webbrowser.open(url)
    print(f"studio open at {url}: record, listen, approve each line, then press Finish", file=sys.stderr, flush=True)
    finished = done.wait(a.timeout)
    srv.shutdown()
    (o / "voice" / "studio.url").unlink(missing_ok=True)
    ls = lines(o)
    approved, missing = [l["id"] for l in ls if l["approved"]], [l["id"] for l in ls if not l["approved"]]
    res = dict(approved=approved, missing=missing, url=url)
    if missing or not finished:
        emit("studio", ok=False, user_action=True, **res,
             message=("Studio closed after the time limit. " if not finished else "") +
                     (f"Still needed: {missing}." if missing else "All lines approved."))
    emit("studio", message=f"All {len(approved)} lines approved. Next: voice.py --provider own", **res)


if __name__ == "__main__":
    main()
