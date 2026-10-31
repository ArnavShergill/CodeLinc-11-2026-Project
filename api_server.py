"""Local HTTP bridge from the LifeMap browser app to AI_interact."""

import json
import os
import time
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from AI_interact import chat_turn
from chat_features import capture_intake, clean_context
from calculator_bridge import calculate, simulate
from learning import make_lesson


ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://arnavshergill.github.io",
}
ALLOWED_ORIGINS.update(
    origin.strip() for origin in os.environ.get("LIFEMAP_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)
MAX_REQUEST_BYTES = 64 * 1024
MAX_MESSAGE_LENGTH = 2000
_requests = {}
_rate_lock = threading.Lock()
_ai_slots = threading.BoundedSemaphore(4)


def allow_request(client, now=None):
    """Per-instance burst control; distributed limits belong at the hosting edge."""
    now = time.monotonic() if now is None else now
    with _rate_lock:
        for key in list(_requests):
            if not _requests[key] or _requests[key][-1] <= now - 60:
                del _requests[key]
        if client not in _requests and len(_requests) >= 2048:
            return False
        recent = _requests.setdefault(client, deque())
        while recent and recent[0] <= now - 60:
            recent.popleft()
        if len(recent) >= 20:
            return False
        recent.append(now)
        return True


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
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path not in ("/api/chat", "/api/intake", "/api/calculate", "/api/scenario", "/api/lesson"):
            self._send_json(404, {"error": "Endpoint not found."})
            return

        origin = self.headers.get("Origin")
        same_origin = origin in ("https://" + self.headers.get("Host", ""), "http://" + self.headers.get("Host", ""))
        if origin and origin not in ALLOWED_ORIGINS and not same_origin:
            self._send_json(403, {"error": "This browser origin is not allowed."})
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
        if self.path in ("/api/calculate", "/api/scenario", "/api/lesson"):
            client = self.client_address[0]
            if not allow_request(client):
                self._send_json(429, {"error": "Please wait a minute before trying again."})
                return
            try:
                if self.path == "/api/calculate":
                    result = {"result": calculate(payload.get("profile", {}))}
                elif self.path == "/api/scenario":
                    result = simulate(payload.get("profile", {}), payload.get("scenario"), payload.get("changes"), payload.get("proposedCoverage"), payload.get("policyYears"))
                else:
                    if not _ai_slots.acquire(blocking=False):
                        self._send_json(429, {"error": "The tutor is busy. Please retry in a moment."})
                        return
                    try:
                        result = {"lesson": make_lesson(payload.get("topic"), payload.get("context", {}))}
                    finally:
                        _ai_slots.release()
                self._send_json(200, result)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
            except Exception:
                self._send_json(502, {"error": "We couldn't prepare this step. Please retry."})
            return
        message = payload.get("message")
        conversation = payload.get("conversation", [])
        if isinstance(message, str) and not message.strip():
            from AI_interact import RATE_FIELDS, RateInputError, normalize_conversational_rate
            raw_context = payload.get("context", {})
            raw_state = raw_context.get("assessment", {}) if isinstance(raw_context, dict) else {}
            field = payload.get("field") if self.path == "/api/intake" else raw_state.get("field") if isinstance(raw_state, dict) else None
            if field in RATE_FIELDS:
                try:
                    normalize_conversational_rate(message)
                except RateInputError as error:
                    self._send_json(400, {"error": str(error)})
                    return
        if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE_LENGTH:
            self._send_json(400, {"error": "Please send between 1 and 2,000 characters."})
            return
        if not isinstance(conversation, list) or len(conversation) > 20 or any(
            not isinstance(turn, dict) or turn.get("role") not in ("user", "assistant")
            or not isinstance(turn.get("content"), str) or len(turn["content"]) > 4000 for turn in conversation
        ):
            self._send_json(400, {"error": "Invalid conversation history."})
            return
        client = self.headers.get("X-Vercel-Forwarded-For", self.client_address[0]) if os.environ.get("VERCEL") else self.client_address[0]
        if not allow_request(client) or not _ai_slots.acquire(blocking=False):
            self._send_json(429, {"error": "Too many requests. Please wait a minute and try again."})
            return

        try:
            context = clean_context(payload.get("context", {}))
            if self.path == "/api/intake":
                result = capture_intake(message, context["profile"], payload.get("field"))
            else:
                result = chat_turn(message, conversation, context)
            self._send_json(200, result)
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except Exception:
            self._send_json(502, {"error": "The AI service is unavailable. Please retry your message."})
        finally:
            _ai_slots.release()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Endpoint not found."})

    def log_message(self, format: str, *args: object) -> None:
        # Do not record chat messages, profiles, credentials, or visitor addresses.
        pass


def main() -> None:
    host = os.environ.get("LIFEMAP_API_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("LIFEMAP_API_PORT", "8000")))
    server = ThreadingHTTPServer((host, port), LifeMapAPIHandler)
    print(f"LifeMap API listening at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LifeMap API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
