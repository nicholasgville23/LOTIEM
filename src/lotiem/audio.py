from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from .same import encode_same_header, same_fsk_samples


def _tone(frequency: float, seconds: float, rate: int, amplitude: float = 0.28) -> bytes:
    return b"".join(
        struct.pack("<h", int(32767 * amplitude * math.sin(2 * math.pi * frequency * i / rate)))
        for i in range(int(rate * seconds))
    )


def _silence(seconds: float, rate: int) -> bytes:
    return bytes(int(rate * seconds) * 2)


def _read_mono_pcm(path: str | Path, rate: int) -> bytes:
    with wave.open(str(path), "rb") as src:
        if src.getnchannels() != 1 or src.getsampwidth() != 2 or src.getframerate() != rate:
            raise ValueError(f"TTS WAV must be mono, 16-bit PCM at {rate} Hz: {path}")
        return src.readframes(src.getnframes())


def build_alert_audio(
    output_path: str | Path,
    *,
    originator: str,
    event_code: str,
    sender: str,
    purge_minutes: int,
    locations: list[str],
    speech_wav: str | Path,
    sample_rate: int = 22050,
    same_repetitions: int = 3,
    eom_repetitions: int = 3,
    attention_tone_hz: float = 1050,
    attention_tone_seconds: float = 8,
) -> Path:
    """Create a local-monitoring WAV: SAME x3, attention tone, speech, EOM x3.

    This creates audio only. It does not key a transmitter or radiate RF.
    """
    if same_repetitions < 1 or eom_repetitions < 1:
        raise ValueError("SAME and EOM repetitions must be at least one")
    header = encode_same_header(originator, event_code, sender, purge_minutes, locations)
    parts: list[bytes] = []
    for index in range(same_repetitions):
        parts.append(bytes().join(struct.pack("<h", x) for x in same_fsk_samples(header, sample_rate)))
        if index + 1 < same_repetitions:
            parts.append(_silence(1.0, sample_rate))
    parts.append(_silence(0.5, sample_rate))
    parts.append(_tone(attention_tone_hz, attention_tone_seconds, sample_rate))
    parts.append(_silence(0.5, sample_rate))
    parts.append(_read_mono_pcm(speech_wav, sample_rate))
    parts.append(_silence(1.0, sample_rate))
    eom = b"NNNN"
    eom_samples = same_fsk_samples(eom, sample_rate)
    for index in range(eom_repetitions):
        parts.append(bytes().join(struct.pack("<h", x) for x in eom_samples))
        if index + 1 < eom_repetitions:
            parts.append(_silence(1.0, sample_rate))

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(b"".join(parts))
    return target
