from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse

from .models import WeatherMessage


class StationHTTPServer:
    """Small authenticated HTTP receiver for an individual simulated station."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        station_id: str,
        on_message: Callable[[WeatherMessage], None],
    ):
        if not token or token == "CHANGE-ME":
            raise ValueError("Set a unique network.api_token before starting a station server")
        self.station_id = station_id
        self.on_message = on_message
        self._token = token.encode("utf-8")
        callback = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, status: int, payload: dict) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                if urlparse(self.path).path == "/health":
                    self._json(200, {"status": "ONLINE", "station_id": callback.station_id})
                else:
                    self._json(404, {"error": "not_found"})

            def do_POST(self) -> None:
                if urlparse(self.path).path != "/api/v1/messages":
                    self._json(404, {"error": "not_found"})
                    return
                supplied = self.headers.get("Authorization", "")
                expected = "Bearer " + callback._token.decode("utf-8")
                if not secrets.compare_digest(supplied, expected):
                    self._json(401, {"error": "unauthorized"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 2 or length > 1_000_000:
                        raise ValueError("Invalid request size")
                    payload = json.loads(self.rfile.read(length))
                    message = WeatherMessage.from_dict(payload)
                    if message.station_ids and callback.station_id not in message.station_ids:
                        self._json(202, {"status": "ignored", "reason": "station_not_targeted"})
                        return
                    callback.on_message(message)
                except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    self._json(400, {"error": "invalid_message", "detail": str(exc)})
                    return
                self._json(202, {"status": "accepted", "station_id": callback.station_id})

            def log_message(self, fmt: str, *args) -> None:
                return

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._server.serve_forever, name=f"{self.station_id}-HTTP", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
