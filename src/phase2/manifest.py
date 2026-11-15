"""Durable local ingestion state and a single-writer lock."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_manifest(path: Path) -> dict:
    if not path.exists():
        return {
            "schema_version": 1,
            "dataset": "BTS Reporting Carrier On-Time Performance",
            "partitions": {},
            "alerts": {},
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not isinstance(state.get("partitions"), dict):
        raise ValueError(f"Unsupported or malformed ingestion manifest: {path}")
    state.setdefault("alerts", {})
    return state


def write_manifest(path: Path, state: dict) -> None:
    """Replace manifest only after the new JSON has been completely written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at_utc"] = utc_now()
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def ingestion_lock(metadata_directory: Path):
    """Prevent two ingestion writers from concurrently publishing partitions."""
    metadata_directory.mkdir(parents=True, exist_ok=True)
    lock_path = metadata_directory / "ingestion.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Another ingestion may be running ({lock_path}). "
            "Confirm the prior process stopped before removing a stale lock."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()}\nstarted_at_utc={utc_now()}\n")
        yield
    finally:
        lock_path.unlink(missing_ok=True)
