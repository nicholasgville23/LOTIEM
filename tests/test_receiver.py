"""Offline unit tests for LOTIEM route fan-out."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lotiem.config import ReceiverSettings
from lotiem.receiver import Receiver


class ReceiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = ReceiverSettings(
            data_dir=Path(self.temp_dir.name),
            routes={
                "BMH": True,
                "WWA": True,
                "LOCAL_OFFICIALS": True,
                "PUBLIC": True,
                "IEMBOT": True,
                "EMAIL": True,
                "WEBSITES": True,
            },
        )
        self.receiver = Receiver(self.settings)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def message(self) -> dict:
        return {
            "seq": 123456789,
            "ts": "2026-11-20T18:30:00Z",
            "topic": "product",
            "from": "LOTWPS",
            "to": "LOTIEM",
            "payload": {
                "product": {"pil": "SVRLOT", "name": "Severe Thunderstorm Warning"},
                "ugc": ["INZ001", "INZ002"],
                "text": "SIMULATED TEST MESSAGE",
                "options": {"routes": ["BMH", "PUBLIC"]},
            },
        }

    def test_dispatch_writes_one_file_per_requested_route(self) -> None:
        routes = self.receiver.dispatch(self.message())
        self.assertEqual(routes, ["BMH", "PUBLIC"])
        for route in routes:
            files = list((Path(self.temp_dir.name) / "routes" / route).glob("*.json"))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["from"], "LOTWPS")
            self.assertEqual(record["text"], "SIMULATED TEST MESSAGE")
        self.assertEqual(self.receiver.stats()["total"], 1)

    def test_disabled_requested_route_is_not_used(self) -> None:
        disabled = dict(self.settings.routes)
        disabled["PUBLIC"] = False
        receiver = Receiver(
            ReceiverSettings(data_dir=Path(self.temp_dir.name) / "second", routes=disabled)
        )
        routes = receiver.dispatch(self.message())
        self.assertEqual(routes, ["BMH"])

    def test_invalid_envelope_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.receiver.dispatch(None)  # type: ignore[arg-type]

    def test_jsonl_audit_record_is_written(self) -> None:
        self.receiver.dispatch(self.message())
        lines = (Path(self.temp_dir.name) / "messages.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["routes"], ["BMH", "PUBLIC"])


if __name__ == "__main__":
    unittest.main()
