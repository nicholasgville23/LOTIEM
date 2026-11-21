# LOTIEM — Receiving and Distribution Service

LOTIEM is the receiving side of the LOTWPS weather-message workflow. LOTWPS creates and edits forecast products, warnings, watches, advisories, statements, and simulated emergency messages; LOTIEM accepts those messages over the local network, records them, and places a copy in each enabled destination queue.

**Companion project:** [LOTWPS — LOT Weather Processing System](https://github.com/nicholasgville23/LOTWPS/tree/feature/voicetext-paul-and-package-layout)

The LOTIEM service in this repository is a small, standalone Python 3.12 receiver. The Tkinter text workstation, BMH network window, transmitter controller, AWIPS-style display, simulated weather engine, and audio player remain in LOTWPS.

## What this build does

- Accepts newline-delimited JSON over TCP from LOTWPS.
- Listens on `0.0.0.0:28894` by default; the configured LAN destination is `10.0.0.117:28894`.
- Validates the JSON envelope and message payload.
- Routes requested messages to enabled queues: `BMH`, `WWA`, `LOCAL_OFFICIALS`, `PUBLIC`, `IEMBOT`, `EMAIL`, and `WEBSITES`.
- Writes a JSON copy into `var/lotiem/routes/<ROUTE>/`, appends a replayable `messages.jsonl` audit log, and stores delivery counters.
- Returns a JSON acknowledgement to the sending LOTWPS client.

The route folders are **outbound queues**, not live integrations. This initial receiver does not log in to email accounts, publish websites, connect to IEMBOT, or contact emergency-management systems. Those adapters need endpoint details, credentials, and their own security review before they can be enabled.

## Install on Windows

Use Python 3.12 from python.org (including Tcl/Tk is useful for the companion LOTWPS GUI, but LOTIEM itself is headless).

```bat
git clone https://github.com/nicholasgville23/LOTIEM.git
cd LOTIEM
copy config\settings.example.json config\settings.json
py -3.12 -m pip install -r requirements.txt
py -3.12 -m lotiem.server
```

Alternatively, run `py -3.12 run_lotiem.py`.

On first run, the service creates its runtime folders under `var/lotiem/`. It uses only the Python standard library; `requirements.txt` is intentionally empty.

## Configure the LOTWPS sender

On the LOTWPS computer, set these values in `config/settings.json`:

```json
{
  "lotiem": {
    "host": "10.0.0.117",
    "port": 28894,
    "transport": "tcp"
  }
}
```

The LOTWPS LAN profile in its feature branch is already set to this address and port. Start **one** LOTIEM listener on the receiving computer before dispatching TCP messages. LOTWPS also contains a compatible embedded LOTIEM service; do not run that listener and this standalone listener on the same IP/port simultaneously.

## Network security

This TCP endpoint is unauthenticated and unencrypted in this simulator build. Keep it on a trusted private LAN or VPN, and create a Windows Firewall inbound rule restricted to the LOTWPS sender and the required private subnet. **Do not expose port 28894 to the public internet.** Add authentication and TLS before using it beyond a trusted lab network.

## Message protocol

LOTWPS opens a TCP connection, sends one UTF-8 JSON object followed by a newline, then waits for one JSON acknowledgement. Example:

```json
{
  "seq": 123456789,
  "ts": "2026-11-20T18:30:00Z",
  "topic": "product",
  "from": "LOTWPS",
  "to": "LOTIEM",
  "payload": {
    "product": {
      "pil": "SVRLOT",
      "name": "Severe Thunderstorm Warning"
    },
    "ugc": ["INZ001", "INZ002"],
    "text": "SIMULATED TEST MESSAGE — THIS IS NOT AN OFFICIAL WARNING.",
    "options": {
      "routes": ["BMH", "PUBLIC"]
    }
  }
}
```

A successful response has `status: "ok"` and the list of routes accepted by the receiver. Requested routes are intersected with the enabled routes in `config/settings.json`; an unavailable route is not silently enabled.

## Run tests

```bat
py -3.12 -m unittest discover -s tests -v
```

## Project status and scope

- Product text and alerts supplied by the companion simulator may be synthetic. Verify all weather information with the National Weather Service before relying on it.
- WXJ75 (Valparaiso, 162.400 MHz) and KBB58 (Gary, 162.425 MHz) are simulated station profiles in LOTWPS. This receiver does not transmit radio signals.
- SAME/EAS audio generation and local playback belong to the simulator. This is not an authorized EAS origination or NOAA Weather Radio transmitter.
- The currently described UI language is English; multilingual support is not implemented in this receiver build.

LOTIEM name note: the repository's current project name is **Chicago Illinois Iowa Environmental Mesonet**; the planned expanded name is **Chicago Illinois Integrated Emergency Manager**.
