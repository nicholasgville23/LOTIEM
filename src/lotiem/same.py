from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def encode_same_header(originator: str, event: str, sender: str, purge_minutes: int,
                       locations: list[str], sequence: int = 0) -> bytes:
    """Build one SAME header burst (ZCZC...N).

    Locations must be six-character SAME location codes. The caller controls
    the three-burst repetition and audio timing.
    """
    if not 0 <= purge_minutes <= 999:
        raise ValueError("purge_minutes must be between 0 and 999")
    if not locations or any(len(x) != 6 or not x.isdigit() for x in locations):
        raise ValueError("locations must contain six-digit SAME codes")
    if len(originator) != 3 or len(event) != 3 or len(sender) != 8:
        raise ValueError("SAME fields require ORG=3, event=3, sender=8 characters")
    header = f"ZCZC-{originator}-{event}-{sender}-{'-'.join(locations)}+{purge_minutes:03d}-{sequence:4d}-"
    return header.encode("ascii")


def same_fsk_samples(data: bytes, sample_rate: int = 22050,
                     mark_hz: float = 2083.0, space_hz: float = 1567.0,
                     baud: int = 520, amplitude: float = 0.65) -> list[int]:
    """Generate mono PCM samples for the standard 520-baud SAME AFSK header."""
    samples_per_bit = sample_rate / baud
    output: list[int] = []
    phase = 0.0
    for byte in data:
        for bit in range(8):
            value = (byte >> bit) & 1
            freq = mark_hz if value else space_hz
            count = round(samples_per_bit)
            for _ in range(count):
                output.append(int(32767 * amplitude * math.sin(phase)))
                phase += 2 * math.pi * freq / sample_rate
                if phase >= 2 * math.pi:
                    phase -= 2 * math.pi
    return output


def write_tone(path: str | Path, frequency_hz: float, seconds: float,
               sample_rate: int = 22050, amplitude: float = 0.35) -> None:
    """Write a mono PCM tone WAV for local simulation/testing."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for i in range(int(sample_rate * seconds)):
        value = int(32767 * amplitude * math.sin(2 * math.pi * frequency_hz * i / sample_rate))
        frames.extend(struct.pack("<h", value))
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)


def write_pcm_wav(path: str | Path, samples: list[int], sample_rate: int = 22050) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(struct.pack("<h", max(-32768, min(32767, x))) for x in samples)
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(raw)
