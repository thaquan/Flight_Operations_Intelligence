"""Download and verify official BTS monthly Reporting Carrier ZIP files."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

from .profile_bts import SOURCE_URL_TEMPLATE


def month_range(start: str, end: str) -> list[str]:
    try:
        start_year, start_month = (int(part) for part in start.split("-"))
        end_year, end_month = (int(part) for part in end.split("-"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Months must use YYYY-MM") from exc
    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        raise ValueError("Months must be in 01..12")
    first, last = start_year * 12 + start_month - 1, end_year * 12 + end_month - 1
    if first > last:
        raise ValueError("Start month must not follow end month")
    return [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(first, last + 1)]


def source_for(month: str, root: Path) -> tuple[str, Path]:
    year, month_number = month.split("-")
    url = SOURCE_URL_TEMPLATE.format(year=year, month=int(month_number))
    return url, root / year / url.rsplit("/", 1)[-1]


def verify_zip(path: Path) -> dict:
    """Hash full ZIP bytes and test the CRC of its one contained CSV."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    with zipfile.ZipFile(path) as archive:
        csv_members = [entry for entry in archive.infolist() if not entry.is_dir() and entry.filename.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError(f"{path.name}: expected one CSV, found {len(csv_members)}")
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise ValueError(f"{path.name}: CRC verification failed for {corrupt_member}")
        member = csv_members[0]
    return {
        "sha256": digest.hexdigest(),
        "zip_bytes": path.stat().st_size,
        "csv_member": member.filename,
        "csv_uncompressed_bytes": member.file_size,
    }


def acquire_one(month: str, root: Path, retries: int = 3) -> dict:
    url, destination = source_for(month, root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        result = verify_zip(destination)
        return {"month": month, "source_url": url, "relative_path": destination.as_posix(), "action": "verified_existing", **result}

    error: Exception | None = None
    for attempt in range(1, retries + 1):
        temporary: Path | None = None
        try:
            request = Request(url, headers={"User-Agent": "FlightOperationsIntelligence/1.0 (academic data project)"})
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".part", prefix=f"bts_{month}_", dir=destination.parent, delete=False) as output:
                temporary = Path(output.name)
                with urlopen(request, timeout=120) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        raise ValueError(f"Unexpected HTML response for {url}")
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        output.write(block)
            result = verify_zip(temporary)
            if destination.exists():
                raise FileExistsError(f"Destination appeared during download: {destination}")
            temporary.rename(destination)
            return {"month": month, "source_url": url, "relative_path": destination.as_posix(), "action": "downloaded", **result}
        except Exception as exc:
            error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 10))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    raise RuntimeError(f"Unable to download {month}: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2025-12")
    parser.add_argument("--root", type=Path, default=Path("data/raw/bts"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/phase1/2024_2025/acquisition_manifest.json"))
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")
    months = month_range(args.start, args.end)
    records: dict[str, dict] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(acquire_one, month, args.root): month for month in months}
        for future in as_completed(futures):
            month = futures[future]
            try:
                result = future.result()
                records[month] = result
                print(f"{month}: {result['action']} ({result['zip_bytes']:,} bytes)", flush=True)
            except Exception as exc:
                failures[month] = str(exc)
                print(f"{month}: FAILED ({exc})", flush=True)
    manifest = {
        "dataset": "BTS Reporting Carrier On-Time Performance (1987-present)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requested_start": args.start,
        "requested_end": args.end,
        "expected_months": len(months),
        "verified_months": len(records),
        "files": [records[month] for month in months if month in records],
        "failures": [{"month": month, "error": failures[month]} for month in sorted(failures)],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    staged = args.manifest.with_suffix(".json.tmp")
    staged.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    staged.replace(args.manifest)
    print(f"Verified {len(records)}/{len(months)} ZIP files; manifest: {args.manifest}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
