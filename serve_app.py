from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from echemdb_ml_pipeline.inference import extract_uploaded_curves


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/features":
            self.send_error(404)
            return
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 20_000_000:
                raise ValueError("Tamanho do arquivo invalido (limite 20 MB)")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Requisicao deve ser um objeto JSON")
            rows = extract_uploaded_curves(data["rows"], data.get("defaults"))
            self.reply(200, {"rows": rows})
        except (ValueError, KeyError, TypeError) as exc:
            self.reply(400, {"error": str(exc)})

    def reply(self, status, data):
        body = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(ROOT / "app")))
    print(f"EchemDB: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()
