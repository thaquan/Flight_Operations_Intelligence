"""Package verified BTS monthly source ZIPs as GitHub Release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from .download_bts import source_for, verify_zip


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    return info


def package_year(year: int, raw_root: Path, source_manifest: dict, destination: Path) -> dict:
    """Write a deterministic outer ZIP containing 12 byte-identical BTS ZIPs."""
    records = {entry["month"]: entry for entry in source_manifest["files"]}
    months = [f"{year}-{month:02d}" for month in range(1, 13)]
    missing = [month for month in months if month not in records]
    if missing:
        raise ValueError(f"Manifest missing months: {missing}")
    sources: list[tuple[str, Path, str]] = []
    for month in months:
        _, source = source_for(month, raw_root)
        expected = records[month]
        inspected = verify_zip(source)
        if inspected["sha256"] != expected["sha256"] or inspected["zip_bytes"] != expected["zip_bytes"]:
            raise ValueError(f"{month}: source ZIP mismatch")
        arcname = f"data/raw/bts/{year}/{source.name}"
        sources.append((arcname, source, inspected["sha256"]))

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    if temporary.exists():
        raise FileExistsError(f"Existing partial archive needs review: {temporary}")
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as output:
            readme = (
                f"BTS Reporting Carrier On-Time Performance, {year}\n"
                "Publisher: U.S. Department of Transportation, Bureau of Transportation Statistics\n"
                "Original monthly files: https://transtats.bts.gov/PREZIP/\n"
                "These are byte-for-byte copies of the official monthly source ZIP files.\n"
                "Check each inner ZIP against SHA256SUMS.txt before use.\n"
            )
            output.writestr(_entry("README_DATASET.txt"), readme.encode("utf-8"))
            checksums = "".join(f"{digest}  {name}\n" for name, _, digest in sources)
            output.writestr(_entry("SHA256SUMS.txt"), checksums.encode("ascii"))
            for name, source, _ in sources:
                with source.open("rb") as original, output.open(_entry(name), "w", force_zip64=True) as target:
                    shutil.copyfileobj(original, target, length=1024 * 1024)
        with zipfile.ZipFile(temporary) as check:
            if len(check.namelist()) != 14 or check.testzip() is not None:
                raise ValueError(f"{year}: packaged ZIP failed CRC or entry count checks")
        temp_hash = sha256_file(temporary)
        if destination.exists():
            if sha256_file(destination) != temp_hash:
                raise FileExistsError(f"Release asset already exists with different content: {destination}")
            temporary.unlink()
            action = "reused"
        else:
            temporary.rename(destination)
            action = "created"
        return {
            "year": year,
            "asset": destination.as_posix(),
            "months": months,
            "zip_bytes": destination.stat().st_size,
            "sha256": temp_hash,
            "action": action,
        }
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/bts"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/phase1/2024_2025/acquisition_manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/tmp/release_assets"))
    args = parser.parse_args()
    source_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    for year in (2024, 2025):
        filename = f"BTS_Reporting_Carrier_{year}_Official_ZIPs.zip"
        result = package_year(year, args.raw_root, source_manifest, args.output_dir / filename)
        print(f"{year}: {result['action']} {result['zip_bytes']:,} bytes, SHA-256 {result['sha256']}", flush=True)


if __name__ == "__main__":
    main()
