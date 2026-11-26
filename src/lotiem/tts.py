from __future__ import annotations

import subprocess
from pathlib import Path


class VoiceTextError(RuntimeError):
    pass


class VoiceTextEngine:
    """Adapter for installed VoiceText command-line binaries.

    VoiceText builds differ in their command-line switches. Set command_template
    in settings.json to the syntax supported by your executable. Supported
    placeholders: {exe}, {text_file}, {output_file}.
    """

    def __init__(self, executable: str, command_template: list[str] | None = None,
                 working_directory: str | None = None):
        self.executable = Path(executable)
        self.command_template = command_template or []
        self.working_directory = working_directory or None

    def synthesize(self, text: str, output_file: str) -> Path:
        if not self.executable.is_file():
            raise VoiceTextError(f"VoiceText executable not found: {self.executable}")
        if not self.command_template:
            raise VoiceTextError(
                "VoiceText command_template is empty. Configure the arguments for "
                "your installed VoiceText Paul executable; its CLI syntax is build-specific."
            )
        output = Path(output_file).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        text_path = output.with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")
        values = {"exe": str(self.executable), "text_file": str(text_path),
                  "output_file": str(output)}
        command = [part.format(**values) for part in self.command_template]
        if command[0] == "{exe}":
            command[0] = str(self.executable)
        subprocess.run(command, cwd=self.working_directory, check=True,
                       capture_output=True, text=True, timeout=180)
        if not output.exists():
            raise VoiceTextError("VoiceText exited without creating the requested WAV file.")
        return output
