from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from .broadcast import BroadcastQueue, MessageArchive
from .models import WeatherMessage, Priority


def load_settings() -> dict:
    path = Path("config/settings.json")
    if not path.exists():
        example = Path("config/settings.example.json")
        if example.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


class TextWorkstation(tk.Tk):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.title(settings["system"]["name"])
        self.geometry("1180x760")
        self.archive = MessageArchive()
        self.queue = BroadcastQueue(self._broadcast_message)
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="KLOT  |  LOTIEM TEXT WORKSTATION",
                  font=("Segoe UI", 16, "bold")).pack(side="left")
        self.clock = ttk.Label(top, text="")
        self.clock.pack(side="right")
        self._tick_clock()

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)
        compose = ttk.Frame(tabs, padding=10)
        bmh = ttk.Frame(tabs, padding=10)
        stations = ttk.Frame(tabs, padding=10)
        tabs.add(compose, text="New Text Message")
        tabs.add(bmh, text="BMH Network")
        tabs.add(stations, text="Stations")

        ttk.Label(compose, text="Product / Hazard").grid(row=0, column=0, sticky="w")
        self.event = tk.StringVar(value="Severe Thunderstorm Warning")
        events = ["Tornado Warning", "Tornado Emergency", "Severe Thunderstorm Warning",
                  "Flash Flood Warning", "Flash Flood Emergency", "Special Weather Statement",
                  "Winter Storm Warning", "Winter Storm Watch", "Blizzard Warning",
                  "Snow Squall Warning", "High Wind Warning", "Required Weekly Test",
                  "Required Monthly Test", "Civil Emergency Message"]
        ttk.Combobox(compose, textvariable=self.event, values=events, width=42).grid(row=0, column=1, sticky="w")
        ttk.Label(compose, text="WMO Header").grid(row=1, column=0, sticky="w", pady=6)
        self.wmo = tk.StringVar(value="WWUS53 KLOT 252003")
        ttk.Entry(compose, textvariable=self.wmo, width=48).grid(row=1, column=1, sticky="w")
        ttk.Label(compose, text="UGC / SAME Location Codes").grid(row=2, column=0, sticky="w")
        self.ugc = tk.StringVar()
        ttk.Entry(compose, textvariable=self.ugc, width=48).grid(row=2, column=1, sticky="w")
        ttk.Label(compose, text="Headline").grid(row=3, column=0, sticky="w", pady=6)
        self.headline = tk.StringVar()
        ttk.Entry(compose, textvariable=self.headline, width=80).grid(row=3, column=1, sticky="ew")
        ttk.Label(compose, text="Message Body").grid(row=4, column=0, sticky="nw", pady=6)
        self.body = tk.Text(compose, height=20, wrap="word")
        self.body.grid(row=4, column=1, sticky="nsew")
        self.send_bmh = tk.BooleanVar(value=True)
        self.send_email = tk.BooleanVar()
        self.send_iembot = tk.BooleanVar()
        self.send_web = tk.BooleanVar()
        opts = ttk.Frame(compose)
        opts.grid(row=5, column=1, sticky="w", pady=8)
        for label, var in [("Send to BMH", self.send_bmh), ("Send to Email", self.send_email),
                           ("Send to IEMBot", self.send_iembot), ("Send to Websites & Outlets", self.send_web)]:
            ttk.Checkbutton(opts, text=label, variable=var).pack(side="left", padx=5)
        ttk.Button(compose, text="Enter / Dispatch Message", command=self._dispatch).grid(row=6, column=1, sticky="e")
        compose.columnconfigure(1, weight=1)
        compose.rowconfigure(4, weight=1)

        ttk.Label(bmh, text="Broadcast Message Handler", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.status = tk.StringVar(value="STOPPED")
        ttk.Label(bmh, textvariable=self.status).pack(anchor="w", pady=5)
        controls = ttk.Frame(bmh)
        controls.pack(anchor="w", pady=8)
        ttk.Button(controls, text="START TX / LOOP", command=self._start).pack(side="left", padx=4)
        ttk.Button(controls, text="STOP TX / LOOP", command=self._stop).pack(side="left", padx=4)
        ttk.Button(controls, text="REFRESH QUEUE", command=self._refresh).pack(side="left", padx=4)
        self.queue_label = ttk.Label(bmh, text="Queue length: 0")
        self.queue_label.pack(anchor="w")
        self.log = tk.Text(bmh, height=24, state="disabled")
        self.log.pack(fill="both", expand=True, pady=8)

        ttk.Label(stations, text="Configured simulated station endpoints",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        for station in self.settings["network"].get("stations", []):
            ttk.Label(stations, text=f'{station["id"]} — {station["city"]}, {station["state"]} — '
                         f'{station["frequency_mhz"]:.3f} MHz — {station["host"]}:{station["port"]}').pack(anchor="w", pady=5)

        self.protocol("WM_DELETE_WINDOW", self._close)

    def _tick_clock(self):
        tz = ZoneInfo(self.settings["system"].get("timezone", "America/Chicago"))
        self.clock.configure(text=datetime.now(tz).strftime("%A %b %d, %Y  %I:%M:%S %p %Z"))
        self.after(1000, self._tick_clock)

    def _dispatch(self):
        event = self.event.get().strip()
        priority = Priority.WARNING if "Warning" in event or "Emergency" in event else (
            Priority.WATCH if "Watch" in event else Priority.STATEMENT)
        message = WeatherMessage(product_id=self.wmo.get().strip(), event=event,
            headline=self.headline.get().strip(), body=self.body.get("1.0", "end").strip(),
            ugc=[x.strip() for x in self.ugc.get().split(",") if x.strip()],
            priority=priority, station_ids=[s["id"] for s in self.settings["network"]["stations"]])
        if not message.body:
            messagebox.showwarning("Message required", "Enter message body text first.")
            return
        self.archive.append(message)
        if self.send_bmh.get():
            self.queue.enqueue(message)
        self._log(f"QUEUED {message.event} [{message.message_id}]")
        self._refresh()

    def _broadcast_message(self, message: WeatherMessage):
        self.after(0, lambda: self._log(f"SIMULATED BROADCAST: {message.event} — {message.headline}"))

    def _start(self):
        self.queue.start(int(self.settings["broadcast"].get("cycle_seconds", 60)))
        self.status.set("RUNNING — SIMULATION")
        self._log("Broadcast loop started.")

    def _stop(self):
        self.queue.stop()
        self.status.set("STOPPED")
        self._log("Broadcast loop stopped.")

    def _refresh(self):
        self.queue_label.configure(text=f"Queue length: {self.queue.queue_length}")

    def _log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _close(self):
        self.queue.stop()
        self.destroy()


def main():
    app = TextWorkstation(load_settings())
    app.mainloop()


if __name__ == "__main__":
    main()
