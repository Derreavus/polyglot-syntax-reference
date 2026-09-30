#!/usr/bin/env python3
"""Serve the local staging build for manual preview.

Usage:
    python scripts/serve_staging.py --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = ROOT / "output" / "staging"


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.address_string()}] {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the generated staging site locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY, help="Directory to serve (default: output/staging)")
    args = parser.parse_args()

    directory = args.directory.resolve()
    if not directory.exists():
        raise SystemExit(f"Preview directory does not exist: {directory}")

    handler = partial(QuietHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {directory} at http://{args.host}:{args.port}/")
        httpd.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
