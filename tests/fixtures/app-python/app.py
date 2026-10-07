import http.server, os
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"<title>Tiny Py</title>ok")
    def log_message(self, *a):
        pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8765"))), H).serve_forever()
