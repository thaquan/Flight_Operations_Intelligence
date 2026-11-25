"""Fixed-scope orchestration adapter; existing pipeline CLIs own all data writes."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONTHS = tuple(f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13))
MANIFEST = Path("docs/phase1/2024_2025/acquisition_manifest.json")


def require_month(month: str) -> str:
    if month not in MONTHS:
        raise ValueError(f"Month outside accepted BTS scope: {month}")
    return month


def verify_source(month: str, root: Path = ROOT) -> dict:
    require_month(month)
    records = json.loads((root / MANIFEST).read_text(encoding="utf-8"))["files"]
    matches = [item for item in records if item["month"] == month]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one source record for {month}")
    item = matches[0]
    path = (root / item["relative_path"]).resolve()
    if not path.is_relative_to((root / "data/raw/bts").resolve()):
        raise ValueError("Source path escapes raw BTS directory")
    if path.stat().st_size != item["zip_bytes"]:
        raise ValueError(f"{month}: source size does not match the manifest")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != item["sha256"]:
        raise ValueError(f"{month}: source checksum does not match the manifest")
    return {"month": month, "source_sha256": digest, "source_bytes": item["zip_bytes"]}


def step_args(step: str, month: str | None = None) -> tuple[str, ...]:
    if step in {"bronze", "silver"}:
        module = "src.phase2.ingest" if step == "bronze" else "src.phase3.load_silver"
        return ("-m", module, "--month", require_month(month))
    if month is not None:
        raise ValueError("Full-scope commands do not accept monthly partitions")
    commands = {
        "silver_reconcile": ("-m", "src.phase3.validate_silver"),
        "dbt_build": ("-m", "src.phase3.dbt_cli", "build", "--threads", "2"),
        "quality": ("-m", "src.phase4.quality_gates", "--mode", "full"),
    }
    if step not in commands:
        raise ValueError(f"Unsupported pipeline step: {step}")
    return commands[step]


class PipelineRunner:
    def __init__(self, root: Path = ROOT, python: Path | None = None):
        self.root = root.resolve()
        default = self.root / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
        self.python = Path(python or os.environ.get("FLIGHT_PIPELINE_PYTHON", default)).resolve()

    def verify(self, month: str) -> dict:
        return verify_source(month, self.root)

    def run(self, step: str, log, month: str | None = None) -> dict:
        args = step_args(step, month)
        if not self.python.is_file():
            raise FileNotFoundError("Pipeline Python is missing; create the Phase 2-4 .venv first")
        command = [str(self.python), *args]
        started = time.monotonic()
        log.info("Executing pipeline step %s (%s)", step, month or "full scope")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        with subprocess.Popen(
            command, cwd=self.root, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        ) as process:
            for line in process.stdout:
                log.info("%s", line.rstrip())
            code = process.wait()
        elapsed = round(time.monotonic() - started, 3)
        if code:
            raise RuntimeError(f"{step} exited with code {code}; inspect Dagster step logs")
        return {"step": step, "scope": month or "2024-2025", "exit_code": code,
                "elapsed_seconds": elapsed}
