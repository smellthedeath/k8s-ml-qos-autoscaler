#!/usr/bin/env python3
import json
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

records = deque(maxlen=20000)

def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    k = int(round((len(values) - 1) * (p / 100)))
    return values[k]

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/record":
            return self._send_json({"error": "not found"}, 404)

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            data = json.loads(raw.decode())
            records.append({
                "ts": time.time(),
                "duration_ms": float(data.get("duration_ms", 0)),
                "failed": int(data.get("failed", 0)),
                "status": int(data.get("status", 0)),
            })
            self._send_json({"ok": True})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 400)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/reset":
            records.clear()
            return self._send_json({"ok": True, "message": "reset done"})

        if parsed.path != "/summary":
            return self._send_json({"error": "not found"}, 404)

        qs = parse_qs(parsed.query)
        window = int(qs.get("window", [30])[0])
        now = time.time()

        recent = [r for r in records if now - r["ts"] <= window]
        durations = [r["duration_ms"] for r in recent]
        total = len(recent)
        failed = sum(r["failed"] for r in recent)

        result = {
            "window_seconds": window,
            "requests": total,
            "failed": failed,
            "failed_rate_percent": round((failed / total) * 100, 3) if total else 0,
            "avg_latency_ms": round(sum(durations) / total, 3) if total else 0,
            "p90_latency_ms": round(percentile(durations, 90), 3) if total else 0,
            "p95_latency_ms": round(percentile(durations, 95), 3) if total else 0,
            "max_latency_ms": round(max(durations), 3) if durations else 0,
        }

        self._send_json(result)

    def log_message(self, fmt, *args):
        return

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 18080), Handler)
    print("metrics_collector listening on :18080")
    server.serve_forever()
