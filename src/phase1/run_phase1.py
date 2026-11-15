"""Profile all verified BTS monthly ZIPs and produce a complete Phase 1 report."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from .download_bts import month_range, source_for
from .profile_bts import profile


def profile_one(month: str, raw_root: Path, profile_dir: Path) -> tuple[str, int, str]:
    _, source = source_for(month, raw_root)
    result = profile(source, month)
    profile_dir.mkdir(parents=True, exist_ok=True)
    target = profile_dir / f"{month}.json"
    temporary = profile_dir / f"{month}.json.tmp"
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return month, result["dataset"]["rows"], result["source"]["zip_sha256"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/bts"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/phase1/2024_2025/acquisition_manifest.json"))
    parser.add_argument("--profile-dir", type=Path, default=Path("docs/phase1/2024_2025/profiles"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true", help="Reuse profiles only if their source SHA-256 matches the manifest")
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected = month_range("2024-01", "2025-12")
    manifest_by_month = {item["month"]: item for item in manifest["files"]}
    if set(manifest_by_month) != set(expected) or manifest.get("failures"):
        raise SystemExit("Acquisition is incomplete; verify all 24 official ZIPs first")

    pending: list[str] = []
    for month in expected:
        target = args.profile_dir / f"{month}.json"
        if args.resume and target.is_file():
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
                if existing["source"]["zip_sha256"] == manifest_by_month[month]["sha256"]:
                    print(f"{month}: reused verified profile ({existing['dataset']['rows']:,} rows)", flush=True)
                    continue
            except (KeyError, ValueError, OSError):
                pass
        pending.append(month)
    failures: list[str] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        jobs = {executor.submit(profile_one, month, args.raw_root, args.profile_dir): month for month in pending}
        for future in as_completed(jobs):
            month = jobs[future]
            try:
                _, rows, sha256 = future.result()
                if sha256 != manifest_by_month[month]["sha256"]:
                    failures.append(f"{month}: ZIP SHA-256 mismatch")
                print(f"{month}: profiled {rows:,} rows", flush=True)
            except Exception as exc:
                failures.append(f"{month}: {exc}")
                print(f"{month}: FAILED ({exc})", flush=True)
    if failures:
        raise SystemExit("Profiling failed:\n" + "\n".join(failures))
    print("All 24 months were profiled. Run: python -m src.phase1.build_report", flush=True)


if __name__ == "__main__":
    main()
