#!/usr/bin/env python3
"""Build the site and serve dist/ for manual preview, rebuilding when sources change.

Usage:
    python scripts/serve_staging.py
    python scripts/serve_staging.py --port 8123 --no-watch

The page you open is always the contents of dist/. The pages at the repository
root are an older frozen copy and are never served by this script.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = ROOT / "dist"
BUILD_SCRIPT = ROOT / "renderer" / "build_site.py"
WATCH_PATHS = (ROOT / "data", ROOT / "src", ROOT / "renderer")


class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        # Never let the browser reuse an older copy of a page, script, or stylesheet.
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.address_string()}] {format % args}")


class PreviewServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR lets a second server bind a port that is already taken, and the
    # older server can keep answering. Refuse the bind there so a stale server is noticed.
    allow_reuse_address = os.name != "nt"

    def server_bind(self) -> None:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        super().server_bind()


def run_build() -> bool:
    result = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=ROOT)
    return result.returncode == 0


def snapshot() -> dict[Path, float]:
    state: dict[Path, float] = {}
    for base in WATCH_PATHS:
        for path in base.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                try:
                    state[path] = path.stat().st_mtime
                except OSError:
                    pass
    return state


def watch_and_rebuild(stop: threading.Event) -> None:
    known = snapshot()
    while not stop.wait(0.7):
        current = snapshot()
        if current == known:
            continue
        time.sleep(0.3)  # let an editor finish writing
        known = snapshot()
        print("\nChange detected, rebuilding...")
        if run_build():
            print("Rebuilt. Refresh the browser.")
        else:
            print("Build failed; still serving the previous output. Fix the error above and save again.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the site and serve dist/ locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY, help="Directory to serve (default: dist)")
    parser.add_argument("--no-build", action="store_true", help="Serve the existing output without building first")
    parser.add_argument("--no-watch", action="store_true", help="Do not rebuild automatically when sources change")
    args = parser.parse_args()

    directory = args.directory.resolve()
    if not args.no_build and directory == DEFAULT_DIRECTORY.resolve():
        print("Building site...")
        if not run_build():
            return 1
    if not (directory / "index.html").is_file():
        raise SystemExit(f"No index.html in {directory}. Run 'python renderer/build_site.py' first.")

    handler = partial(PreviewHandler, directory=str(directory))
    try:
        httpd = PreviewServer((args.host, args.port), handler)
    except OSError as error:
        raise SystemExit(
            f"Could not start on port {args.port}: {error}\n"
            "Another preview server is probably still running and would keep serving its old folder.\n"
            f"Stop it (Ctrl+C in its terminal) or use a different port, for example --port {args.port + 1}."
        )

    stop = threading.Event()
    if not args.no_watch and directory == DEFAULT_DIRECTORY.resolve():
        threading.Thread(target=watch_and_rebuild, args=(stop,), daemon=True).start()
        print("Watching data/, src/ and renderer/ for changes.")

    with httpd:
        print(f"Serving {directory}")
        print(f"Open http://{args.host}:{args.port}/   (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
