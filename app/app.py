from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import time
import urllib.parse

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = time.time()

        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        loops = int(params.get("loops", ["120000"])[0])

        data = b"master-thesis-kubernetes-ml-autoscaling"
        result = data

        for _ in range(loops):
            result = hashlib.sha256(result).digest()

        duration_ms = round((time.time() - start) * 1000, 2)

        body = f"OK loops={loops} duration_ms={duration_ms}\n"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        return

server = HTTPServer(("0.0.0.0", 8080), Handler)
print("CPU test app listening on port 8080")
server.serve_forever()
