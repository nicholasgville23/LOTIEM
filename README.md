# LOTIEM / LOTWPS

LOTWPS is the simulated Chicago/Romeoville and Northwest Indiana weather-processing and message-distribution framework. LOTIEM receives those messages and routes them to station queues, local audio feeds, and configured downstream outlets.

## Current implementation

- Python 3.13+ and Tkinter workstation.
- JSON configuration with America/Chicago timezone.
- Priority-based weather-message queue and JSONL archive.
- SAME header FSK audio generation and 1050 Hz attention-tone generation.
- VoiceText command adapter for a locally installed Paul executable.
- Authenticated HTTP station receiver service.
- WAV alert assembly for local monitoring: SAME header bursts, attention tone, supplied TTS WAV, and EOM bursts.

This project is a **simulation and local audio-feed system**. It does not transmit on NOAA Weather Radio frequencies or control an RF transmitter. Verify generated alerts before distributing them to real users.

## Install

```powershell
py -3.13 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the workstation with `lotiem`. On first launch, `config/settings.example.json` is copied to `config/settings.json`. Edit the local settings file; do not commit API tokens, private network details, or proprietary voice binaries.

## VoiceText Paul

VoiceText command-line switches vary by binary build. Set `audio.command_template` to the exact arguments supported by your installed executable. Supported placeholders are `{exe}`, `{text_file}`, and `{output_file}`. Example shape (not a universal VoiceText command):

```json
"command_template": ["{exe}", "--input", "{text_file}", "--output", "{output_file}"]
```

The adapter intentionally does not guess undocumented switches. Keep VoiceText executables and DLLs on the local Windows machine; do not upload proprietary binaries.

## Station receiver API

Each station process can host its own receiver. The receiver requires a unique bearer token and exposes `GET /health` and `POST /api/v1/messages` with a `WeatherMessage` JSON body and `Authorization: Bearer <token>`. Bind to a trusted LAN interface only, restrict access with Windows Firewall, and use a unique token per deployment.

## Audio assembly API

Call `lotiem.audio.build_alert_audio(...)` after synthesizing the spoken message to a mono, 16-bit PCM WAV at the configured sample rate. The output is a single WAV suitable for a local monitoring feed or test playback.
