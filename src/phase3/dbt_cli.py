"""Run dbt using the ignored local .env and versioned dbt profile."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from .config import PROJECT_ROOT, read_env


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m src.phase3.dbt_cli <dbt arguments>")
    settings = read_env(PROJECT_ROOT / ".env")
    environment = os.environ.copy()
    environment.update(settings)
    dbt_executable = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
    if not dbt_executable.is_file():
        raise FileNotFoundError("dbt is not installed in this Python environment")
    dbt_root = PROJECT_ROOT / "dbt"
    command = [
        str(dbt_executable),
        *sys.argv[1:],
        "--project-dir", str(dbt_root),
        "--profiles-dir", str(dbt_root),
    ]
    raise SystemExit(subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=False).returncode)


if __name__ == "__main__":
    main()
