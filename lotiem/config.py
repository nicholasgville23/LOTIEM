"""Settings for the standalone LOTIEM receiver."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTES = (
    "BMH",
    "WWA",
    "LOCAL_OFFICIALS",
    "PUBLIC",
    "IEMBOT",
    "EMAIL",
    "WEBSITES",
)


@dataclass(frozen=True, slots=True)
class ReceiverSettings:
    bind_host: str = "0.0.0.0"
    advertised_host: str = "10.0.0.117"
    port: int = 28894
    data_dir: Path = field(default_factory=lambda: ROOT / "var" / "lotiem")
    routes: dict[str, bool] = field(
        default_factory=lambda: {name: True for name in DEFAULT_ROUTES}
    )
    max_message_bytes: int = 1_048_576

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ReceiverSettings":
        settings_path = Path(path) if path else ROOT / "config" / "settings.json"
        if not settings_path.is_absolute():
            settings_path = ROOT / settings_path
        payload: dict[str, Any] = {}
        if settings_path.is_file():
            try:
                payload = json.loads(settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Could not read LOTIEM settings at {settings_path}: {exc}") from exc

        network = payload.get("network", {}) or {}
        route_config = payload.get("routes", {}) or {}
        route_flags = {name: bool(route_config.get(name, True)) for name in DEFAULT_ROUTES}
        data_dir = Path(payload.get("data_dir", ROOT / "var" / "lotiem")).expanduser()
        if not data_dir.is_absolute():
            data_dir = (ROOT / data_dir).resolve()

        try:
            port = int(network.get("port", 28894))
            max_bytes = int(network.get("max_message_bytes", 1_048_576))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("LOTIEM port and max_message_bytes must be integers") from exc
        if not (1 <= port <= 65535):
            raise RuntimeError("LOTIEM network.port must be between 1 and 65535")
        if not (1024 <= max_bytes <= 16_777_216):
            raise RuntimeError("LOTIEM network.max_message_bytes must be 1024..16777216")

        return cls(
            bind_host=str(network.get("bind_host", "0.0.0.0")),
            advertised_host=str(network.get("host", "10.0.0.117")),
            port=port,
            data_dir=data_dir,
            routes=route_flags,
            max_message_bytes=max_bytes,
        )
