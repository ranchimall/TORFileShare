"""Tiny HTTP server that exposes the shared folder over three endpoints:

  GET  /list                -> JSON {relative_path: {sha256, size, mtime}, ...}
  GET  /file/<relative/path> -> raw bytes of that file
  POST /file/<relative/path> -> body bytes are written into the shared folder

Relative paths can include subfolders (e.g. /file/photos/trip/img1.jpg).
safe_join() in utils.py guarantees nothing can escape the shared folder,
regardless of what a peer sends (no "..", no absolute paths).

It only ever binds to 127.0.0.1 -- it's reached from the outside solely
via the Tor hidden service, which forwards to this port.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from utils import list_shared_files, safe_join


class SyncHandler(BaseHTTPRequestHandler):
    shared_dir = None
    recently_received = None  # dict: relative_path -> mtime, shared with sync.py

    def log_message(self, fmt, *args):
        # Quiet by default. Comment this out (or call super()) to debug.
        pass

    def _resolve(self, raw_path):
        """Turn the URL tail after /file/ into a safe (full_path, rel_path)
        pair, or return (None, None) if invalid."""
        try:
            return safe_join(self.shared_dir, unquote(raw_path))
        except ValueError:
            return None, None

    def do_GET(self):
        if self.path == "/list":
            files = list_shared_files(self.shared_dir)
            body = json.dumps(files).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/file/"):
            full, rel = self._resolve(self.path[len("/file/"):])
            if full is None:
                self.send_response(400)
                self.end_headers()
                return
            if os.path.isfile(full):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(os.path.getsize(full)))
                self.end_headers()
                with open(full, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/file/"):
            full, rel = self._resolve(self.path[len("/file/"):])
            if full is None:
                self.send_response(400)
                self.end_headers()
                return
            os.makedirs(os.path.dirname(full), exist_ok=True)
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            tmp = full + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, full)
            if self.recently_received is not None:
                self.recently_received[rel] = os.path.getmtime(full)
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def start_server(shared_dir, http_port, recently_received):
    SyncHandler.shared_dir = shared_dir
    SyncHandler.recently_received = recently_received
    server = ThreadingHTTPServer(("127.0.0.1", http_port), SyncHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
