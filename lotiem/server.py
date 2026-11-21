"""TCP JSON-lines server compatible with the LOTWPS Bus client."""
from __future__ import annotations

import json
import socketserver
from pathlib import Path

from .config import ReceiverSettings
from .receiver import Receiver, _utc_stamp


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        service: "LOTIEMServer" = self.server.lotiem  # type: ignore[attr-defined]
        try:
            raw = self.rfile.readline(service.settings.max_message_bytes + 1)
        except OSError:
            return
        if not raw:
            return
        if len(raw) > service.settings.max_message_bytes:
            self._reply({"status": "error", "error": "message exceeds configured size limit"})
            return
        try:
            message = json.loads(raw.decode("utf-8"))
            routes = service.receiver.dispatch(message)
            reply = {
                "status": "ok",
                "seq": message.get("seq"),
                "routes": routes,
                "received": _utc_stamp(),
            }
            service.accepted += 1
            service._log(f"accepted {message.get('topic', '?')} from {message.get('from', '?')} -> {','.join(routes)}")
            self._reply(reply)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._reply({"status": "error", "error": str(exc)})
        except Exception as exc:  # keep one bad client from terminating the listener
            service._log(f"request error: {type(exc).__name__}: {exc}")
            self._reply({"status": "error", "error": "internal receiver error"})

    def _reply(self, payload: dict) -> None:
        try:
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
            self.wfile.flush()
        except OSError:
            pass


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class LOTIEMServer:
    def __init__(
        self,
        settings: ReceiverSettings | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self.settings = settings or ReceiverSettings.load()
        bind_host = host or self.settings.bind_host
        bind_port = int(port or self.settings.port)
        self.receiver = Receiver(self.settings)
        self.accepted = 0
        self._server = _ThreadingTCPServer((bind_host, bind_port), _Handler)
        self._server.lotiem = self  # type: ignore[attr-defined]
        self._log_file = self.settings.data_dir / "server.log"

    def _log(self, line: str) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        with self._log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{_utc_stamp()} {line}\n")

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def serve_forever(self) -> None:
        host, port = self.address
        print(f"LOTIEM receiver listening on {host}:{port}")
        self._log(f"listener started on {host}:{port}")
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            print("LOTIEM receiver stopping")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        try:
            self._server.shutdown()
        except Exception:
            pass
        self._server.server_close()
        self._log(f"listener stopped; accepted {self.accepted} messages")


def main() -> None:
    LOTIEMServer().serve_forever()


if __name__ == "__main__":
    main()
