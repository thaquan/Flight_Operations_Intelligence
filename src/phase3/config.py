"""Local-only PostgreSQL connection settings, never committed as credentials."""

from __future__ import annotations

import os
from pathlib import Path
import re
import secrets


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_KEYS = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT")
DEFAULTS = {
    "POSTGRES_DB": "flight_warehouse",
    "POSTGRES_USER": "flight_app",
    "POSTGRES_PORT": "5433",
}


def bootstrap_env(path: Path) -> bool:
    """Create a strong local .env once; never replace existing credentials."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = {**DEFAULTS, "POSTGRES_PASSWORD": secrets.token_urlsafe(32)}
    contents = "".join(f"{key}={settings[key]}\n" for key in REQUIRED_KEYS)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(contents)
    if os.name != "nt":
        path.chmod(0o600)
    return True


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing local configuration: {path}. Run bootstrap_env first.")
    settings: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if "=" not in text:
            raise ValueError(f"Invalid configuration line in {path.name}")
        key, value = (part.strip() for part in text.split("=", 1))
        if key in settings:
            raise ValueError(f"Duplicate setting: {key}")
        settings[key] = value.strip('"').strip("'")
    missing = [key for key in REQUIRED_KEYS if not settings.get(key)]
    if missing:
        raise ValueError(f"Missing local settings: {', '.join(missing)}")
    for name in ("POSTGRES_DB", "POSTGRES_USER"):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", settings[name]):
            raise ValueError(f"Invalid PostgreSQL identifier in {name}")
    password = settings["POSTGRES_PASSWORD"]
    if len(password) < 20 or password.startswith("REPLACE_"):
        raise ValueError("POSTGRES_PASSWORD must be a strong non-placeholder secret")
    try:
        port = int(settings["POSTGRES_PORT"])
    except ValueError as exc:
        raise ValueError("POSTGRES_PORT must be numeric") from exc
    if not 1024 <= port <= 65535:
        raise ValueError("POSTGRES_PORT must be between 1024 and 65535")
    return {key: settings[key] for key in REQUIRED_KEYS}
