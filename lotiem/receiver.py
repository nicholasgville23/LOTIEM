"""Validated JSON receiver and local route-queue fan-out."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DEFAULT_ROUTES, ReceiverSettings


_CENTRAL = ZoneInfo("America/Chicago")


def _safe_name(value: object, fallback: str = "MESSAGE") -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_")
    return token[:40] or fallback


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Receiver:
    """Receives a LOTWPS message, persists it, and fans it out to local queues."""

    def __init__(self, settings: ReceiverSettings | None = None) -> None:
        self.settings = settings or ReceiverSettings.load()
        self.root = self.settings.data_dir
        self.routes_dir = self.root / "routes"
        self.log_file = self.root / "messages.jsonl"
        self.state_file = self.root / "state.json"
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._total = 0
        self._counts = {route: 0 for route in DEFAULT_ROUTES}
        self._load_state()

    def _load_state(self) -> None:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self._total = max(0, int(state.get("total", 0)))
        for route, count in (state.get("counts") or {}).items():
            if route in self._counts:
                self._counts[route] = max(0, int(count))

    def enabled_routes(self) -> list[str]:
        return [route for route in DEFAULT_ROUTES if self.settings.routes.get(route, False)]

    def routes_for(self, message: dict) -> list[str]:
        payload = message.get("payload", {}) or {}
        options = payload.get("options", {}) or {}
        requested = options.get("routes") or payload.get("routes")
        enabled = set(self.enabled_routes())
        if requested is None:
            return [route for route in DEFAULT_ROUTES if route in enabled]
        if isinstance(requested, str):
            requested = [requested]
        if not isinstance(requested, list):
            raise ValueError("payload.options.routes must be a list of route names")
        normalized = []
        for route in requested:
            name = str(route).upper()
            if name in DEFAULT_ROUTES and name in enabled and name not in normalized:
                normalized.append(name)
        return normalized

    def _atomic_json(self, path: Path, payload: dict) -> None:
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _append_log(self, record: dict) -> None:
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def dispatch(self, message: dict) -> list[str]:
        if not isinstance(message, dict):
            raise ValueError("message must be a JSON object")
        payload = message.get("payload", {}) or {}
        if not isinstance(payload, dict):
            raise ValueError("message.payload must be an object")
        text = payload.get("text", "")
        if text is None:
            text = ""
        if not isinstance(text, str):
            raise ValueError("payload.text must be a string")
        product = payload.get("product", {}) or {}
        if not isinstance(product, dict):
            raise ValueError("payload.product must be an object")
        subscribers = payload.get("subscribers", {}) or {}
        if not isinstance(subscribers, dict):
            subscribers = {}

        routes = self.routes_for(message)
        received = _utc_stamp()
        central_stamp = datetime.now(_CENTRAL).strftime("%Y%m%d-%H%M%S-%f")
        product_id = _safe_name(product.get("pil") or product.get("code"), "SPS")
        with self._lock:
            self._total += 1
            local_seq = self._total
            for route in routes:
                route_payload = {
                    "seq": message.get("seq"),
                    "route": route,
                    "subscriber": subscribers.get(route, ""),
                    "from": str(message.get("from", "")),
                    "to": str(message.get("to", "")),
                    "topic": str(message.get("topic", "")),
                    "subject": str(payload.get("subject") or product.get("name", "")),
                    "product": product,
                    "ugc": payload.get("ugc", []),
                    "text": text,
                    "received": received,
                    "receiver_sequence": local_seq,
                }
                folder = self.routes_dir / route
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{central_stamp}-{local_seq:08d}-{product_id}.json"
                self._atomic_json(path, route_payload)
                self._counts[route] = self._counts.get(route, 0) + 1

            log_record = {
                "receiver_sequence": local_seq,
                "seq": message.get("seq"),
                "ts": message.get("ts") or received,
                "from": str(message.get("from", "")),
                "to": str(message.get("to", "")),
                "topic": str(message.get("topic", "")),
                "product": product.get("pil") or product.get("code", ""),
                "name": product.get("name", ""),
                "subject": payload.get("subject", ""),
                "routes": routes,
                "characters": len(text),
                "preview": text[:160].replace("\n", " "),
                "received": received,
            }
            self._append_log(log_record)
            self._atomic_json(
                self.state_file,
                {"total": self._total, "counts": self._counts, "updated": received},
            )
        return routes

    def stats(self) -> dict:
        with self._lock:
            return {
                "service": "LOTIEM",
                "host": self.settings.advertised_host,
                "bind_host": self.settings.bind_host,
                "port": self.settings.port,
                "total": self._total,
                "routes": dict(self._counts),
                "enabled": self.enabled_routes(),
                "data_dir": str(self.root),
            }
