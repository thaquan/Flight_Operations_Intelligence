"""Compare Parquet compression settings on one verified source month."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

import pyarrow.parquet as pq

from src.phase1.download_bts import verify_zip
from .bronze_writer import write_bronze
from .ingest import BronzePipeline, PROJECT_ROOT
from .manifest import utc_now


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default="2024-01")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--report", type=Path, default=Path("docs/phase2/compression_benchmark.json"))
    args = parser.parse_args()
    pipeline = BronzePipeline(project_root=args.project_root)
    source = pipeline.sources[args.month]
    source_path = pipeline._source_path(source)
    checked = verify_zip(source_path)
    if checked["sha256"] != source["sha256"]:
        raise ValueError("Source ZIP checksum differs from Phase 1")

    output_root = pipeline.project_root / "data/tmp/phase2_benchmark"
    output_root.mkdir(parents=True, exist_ok=True)
    output_dir = Path(tempfile.mkdtemp(prefix=f"{args.month}-", dir=output_root))
    measurements = []
    for compression in ("snappy", "zstd"):
        output = output_dir / f"{args.month}-{compression}.parquet"
        began = time.perf_counter()
        result = write_bronze(
            source_path, source["csv_member"], args.month, source["sha256"],
            output, pipeline.source_fields, compression=compression,
        )
        elapsed = time.perf_counter() - began
        if pq.read_metadata(output).num_rows != pipeline.expected_rows[args.month]:
            raise ValueError(f"Benchmark {compression}: unexpected row count")
        measurements.append({
            "compression": compression,
            "rows": result["bronze_row_count"],
            "parquet_bytes": result["parquet_bytes"],
            "elapsed_seconds": round(elapsed, 3),
            "rows_per_second": round(result["bronze_row_count"] / elapsed, 1),
            "row_groups": pq.read_metadata(output).num_row_groups,
        })

    report = {
        "generated_at_utc": utc_now(),
        "source_month": args.month,
        "source_zip_sha256": source["sha256"],
        "source_csv_uncompressed_bytes": source["csv_uncompressed_bytes"],
        "benchmark_scope": "conversion plus Parquet hashing; ZIP verification excluded from timed section",
        "output_directory": str(output_dir.relative_to(pipeline.project_root)),
        "measurements": measurements,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
