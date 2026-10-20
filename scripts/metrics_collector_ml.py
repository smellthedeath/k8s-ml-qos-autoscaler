#!/usr/bin/env python3

import json
import time
import os
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


DATA_DIR = "dataset"
DATA_FILE = os.path.join(DATA_DIR, "raw_metrics.jsonl")


os.makedirs(DATA_DIR, exist_ok=True)


records = deque(maxlen=50000)


def percentile(values, p):
    if not values:
        return 0

    values = sorted(values)

    index = int(round((len(values)-1) * p/100))

    return values[index]


def save_record(record):

    with open(DATA_FILE, "a") as f:
        f.write(
            json.dumps(record)
            + "\n"
        )


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, code=200):

        body = json.dumps(data).encode()

        self.send_response(code)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)


    def do_POST(self):

        if self.path != "/record":
            return self.send_json(
                {"error":"not found"},
                404
            )


        length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )


        raw = self.rfile.read(length)


        data = json.loads(
            raw.decode()
        )


        record = {

            "ts": time.time(),

            "duration_ms":
                float(
                    data.get(
                        "duration_ms",
                        0
                    )
                ),

            "failed":
                int(
                    data.get(
                        "failed",
                        0
                    )
                ),

            "status":
                int(
                    data.get(
                        "status",
                        0
                    )
                )
        }


        records.append(record)

        save_record(record)


        self.send_json(
            {
                "ok":True
            }
        )



    def do_GET(self):

        parsed = urlparse(
            self.path
        )


        if parsed.path == "/reset":

            records.clear()

            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)


            return self.send_json(
                {
                    "ok":True
                }
            )


        if parsed.path != "/summary":

            return self.send_json(
                {
                    "error":"not found"
                },
                404
            )


        qs = parse_qs(
            parsed.query
        )


        window = int(
            qs.get(
                "window",
                [30]
            )[0]
        )


        now = time.time()


        recent = [

            r for r in records

            if now-r["ts"] <= window

        ]


        durations = [

            r["duration_ms"]

            for r in recent

        ]


        total = len(recent)

        failed = sum(
            r["failed"]
            for r in recent
        )


        result = {

            "window_seconds": window,

            "requests": total,

            "failed": failed,

            "failed_rate_percent":
                round(
                    (failed/total)*100,
                    3
                )
                if total else 0,


            "avg_latency_ms":
                round(
                    sum(durations)/total,
                    3
                )
                if total else 0,


            "p95_latency_ms":
                round(
                    percentile(
                        durations,
                        95
                    ),
                    3
                )
                if total else 0
        }


        self.send_json(result)



    def log_message(self, *args):
        return



if __name__ == "__main__":

    print(
        "ML Metrics Collector :18081"
    )

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            18081
        ),
        Handler
    )

    server.serve_forever()
