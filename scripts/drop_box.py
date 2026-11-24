#!/usr/bin/env python3
"""Lightweight Memory & File Drop Box Daemon for NL1.
Saves uploaded files into /home/bule/multi-ai-chat/imported_memories
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import re
import sys

UPLOAD_DIR = "/home/bule/multi-ai-chat/imported_memories"
HTML_FILE = "/home/bule/multi-ai-chat/scripts/drop_box.html"
PORT = 8999

os.makedirs(UPLOAD_DIR, exist_ok=True)

class DropBoxHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(f"[DropBox] {self.address_string()} - {format % args}\n")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path in ("", "/drop-box"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(HTML_FILE, "rb") as f:
                self.wfile.write(f.read())
        elif clean_path == "/drop-box/list":
            files = []
            if os.path.exists(UPLOAD_DIR):
                for name in sorted(os.listdir(UPLOAD_DIR)):
                    path = os.path.join(UPLOAD_DIR, name)
                    if os.path.isfile(path):
                        files.append({"name": name, "size": os.path.getsize(path)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(files).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/drop-box/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Expected multipart/form-data")
                return

            boundary_match = re.search(r'boundary=([^\s;]+)', content_type)
            if not boundary_match:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing boundary")
                return

            boundary = boundary_match.group(1).encode("utf-8")
            if boundary.startswith(b'"') and boundary.endswith(b'"'):
                boundary = boundary[1:-1]

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            parts = body.split(b"--" + boundary)
            saved = []
            for part in parts:
                if not part or part in (b"--\r\n", b"--", b"--\r\n\r\n"):
                    continue
                header_data, sep, file_data = part.partition(b"\r\n\r\n")
                if not sep:
                    continue
                file_data = file_data.rstrip(b"\r\n")
                header_text = header_data.decode("utf-8", errors="ignore")
                fn_match = re.search(r'filename="([^"]+)"', header_text)
                if fn_match:
                    raw_filename = fn_match.group(1)
                    filename = os.path.basename(raw_filename.replace("\\", "/"))
                    if filename:
                        target_path = os.path.join(UPLOAD_DIR, filename)
                        with open(target_path, "wb") as f:
                            f.write(file_data)
                        saved.append(filename)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "saved": saved}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(("127.0.0.1", PORT), DropBoxHandler)
    print(f"DropBox running on http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
