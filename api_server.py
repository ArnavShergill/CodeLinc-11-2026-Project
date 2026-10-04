"""Local HTTP bridge from the LifeMap browser app to AI_interact."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from AI_interact import API_request


ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
}
MAX_REQUEST_BYTES = 64 * 1024


class LifeMapAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if origin not in ALLOWED_ORIGINS:
            self._send_json(403, {"error": "This browser origin is not allowed."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Endpoint not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self._send_json(413, {"error": "Request body is empty or too large."})
                return
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Request body must be a JSON object."})
            return
        message = payload.get("message")
        conversation = payload.get("conversation", [])
        if not isinstance(message, str) or not message.strip():
            self._send_json(400, {"error": "A non-empty message is required."})
            return
        if not isinstance(conversation, list):
            self._send_json(400, {"error": "Conversation must be a list."})
            return

        try:
            reply = API_request(message, conversation)
        except (RuntimeError, ValueError) as error:
            self._send_json(502, {"error": str(error)})
            return
        self._send_json(200, {"reply": reply})

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Endpoint not found."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    host = os.environ.get("LIFEMAP_API_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, 8000), LifeMapAPIHandler)
    print(f"LifeMap API listening at http://{host}:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LifeMap API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
