from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class CommandError(RuntimeError):
    pass


class Runner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        capture: bool = False,
    ) -> str: ...


class SubprocessRunner:
    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        capture: bool = False,
    ) -> str:
        try:
            result = subprocess.run(
                list(args),
                cwd=cwd,
                check=True,
                text=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
            )
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "").strip()
            command = " ".join(args)
            suffix = f": {detail}" if detail else ""
            raise CommandError(
                f"command failed ({command}){suffix}"
            ) from error
        return result.stdout.strip() if capture else ""
