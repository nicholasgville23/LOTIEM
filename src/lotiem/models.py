from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from uuid import uuid4


class Priority(IntEnum):
    STATEMENT = 10
    ADVISORY = 20
    WATCH = 30
    WARNING = 40
    EMERGENCY = 50


@dataclass(slots=True)
class WeatherMessage:
    product_id: str
    event: str
    headline: str
    body: str
    sender: str = "KLOT"
    ugc: list[str] = field(default_factory=list)
    station_ids: list[str] = field(default_factory=list)
    priority: Priority = Priority.STATEMENT
    action: str = "NEW"
    expires_at: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    same_event_code: str | None = None

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id, "product_id": self.product_id,
            "event": self.event, "headline": self.headline, "body": self.body,
            "sender": self.sender, "ugc": self.ugc, "station_ids": self.station_ids,
            "priority": int(self.priority), "action": self.action,
            "expires_at": self.expires_at, "created_at": self.created_at,
            "same_event_code": self.same_event_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeatherMessage":
        return cls(
            product_id=str(data["product_id"]), event=str(data["event"]),
            headline=str(data.get("headline", "")), body=str(data.get("body", "")),
            sender=str(data.get("sender", "KLOT")), ugc=list(data.get("ugc", [])),
            station_ids=list(data.get("station_ids", [])),
            priority=Priority(int(data.get("priority", 10))),
            action=str(data.get("action", "NEW")), expires_at=data.get("expires_at"),
            message_id=str(data.get("message_id") or uuid4()),
            created_at=str(data.get("created_at") or datetime.now(timezone.utc).isoformat()),
            same_event_code=data.get("same_event_code"),
        )
