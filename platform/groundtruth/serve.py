"""Serving the operational system on localhost.

The three interfaces read real figures computed from this machine's database.
They are not published: the public site carries the explanation, this carries
the working system.

The server binds to the loopback address only. That is deliberate and enforced
rather than assumed -- an operator running this on a laptop on a shared network
should not find they have exposed a dashboard to it.
"""
from __future__ import annotations

import http.server
import socket
import socketserver
import threading
import webbrowser
from functools import partial
from pathlib import Path

LOOPBACK = "127.0.0.1"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the app directory, logging one line per request."""

    def log_message(self, fmt, *args):  # noqa: A003 - stdlib signature
        code = args[1] if len(args) > 1 else "?"
        path = args[0].split(" ")[1] if args else "?"
        if str(code).startswith(("4", "5")):
            print(f"  {code}  {path}")

    def end_headers(self):
        # Nothing here should ever be cached by a browser between runs: the
        # payload changes every time the platform is rebuilt.
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()


def free_port(preferred: int) -> int:
    """Return the preferred port, or the next free one."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((LOOPBACK, port))
                return port
            except OSError:
                continue
    raise OSError(f"no free port in {preferred}-{preferred + 19}")


def check_payload(app_dir: Path) -> tuple[bool, str]:
    """Is there platform output to serve?"""
    payload = Path(app_dir) / "data" / "platform.json"
    if not payload.exists():
        return False, "no platform output — run: gt run"
    import json
    try:
        d = json.loads(payload.read_text())
    except json.JSONDecodeError as exc:
        return False, f"platform.json is unreadable: {exc}"
    built = d.get("built_systems") or []
    return bool(built), (f"{len(built)} systems, computed {d.get('generated', 'unknown')}"
                         if built else "platform.json contains no system output")


def serve(app_dir: Path, port: int = 8787, open_browser: bool = True) -> None:
    app_dir = Path(app_dir).resolve()
    if not (app_dir / "index.html").exists():
        raise FileNotFoundError(f"no interface at {app_dir}")

    port = free_port(port)
    handler = partial(QuietHandler, directory=str(app_dir))

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server((LOOPBACK, port), handler) as httpd:
        host, bound = httpd.server_address[:2]
        assert host == LOOPBACK, "server must bind to loopback only"
        url = f"http://{LOOPBACK}:{bound}/index.html"
        ok, detail = check_payload(app_dir)
        print(f"  {'ready' if ok else 'no data'}   {detail}")
        print(f"  public   {url}")
        print(f"  admin    http://{LOOPBACK}:{bound}/admin.html")
        print(f"  mobile   http://{LOOPBACK}:{bound}/mobile.html")
        print(f"\n  bound to {LOOPBACK} only — not reachable from the network")
        print("  ctrl-c to stop")
        if open_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  stopped")
