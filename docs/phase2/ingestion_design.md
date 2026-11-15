# Ingestion, Idempotency and Recovery Design

## Source of truth

The acquisition manifest and aggregate profile produced in Phase 1 define:

- The accepted monthly ZIP path, URL, ZIP byte length, CSV member and SHA-256.
- The expected row count for every month.
- The shared 109-column source schema.

The ingestion pipeline refuses to accept changed source bytes without the Phase 1 evidence being refreshed and reviewed. It does not silently trust filenames.

## Processing sequence

1. Resolve one month from the source catalog.
2. Take an exclusive local ingestion lock.
3. Check whether the current manifest and Parquet metadata already match.
4. For new work, verify the source ZIP hash, size, CSV member and CRC.
5. Record a `running` state in the manifest.
6. Stream CSV batches to a unique `_staging` directory, adding row-level lineage.
7. Validate monthly row count and the full 113-field Parquet schema.
8. Publish the partition directory and record `completed`.
9. Release the lock.

The manifest is stored at `data/bronze/_metadata/ingestion_manifest.json`. It is written through a temporary JSON file and a rename to avoid exposing partially written JSON.

## Incremental ingestion

The entrypoint accepts one month or an inclusive month range. A successfully completed partition whose source SHA-256, size, schema and row count match is skipped. The ZIP is rehashed on a skip, so a changed local source cannot masquerade as the verified earlier input.

A repeated 24-month invocation was measured to produce 24 skips in 3.918 seconds with the ingestion manifest's SHA-256 unchanged.

## Controlled reprocessing

`--reprocess` explicitly requests a partition replacement. A new partition is fully written and validated in staging before the previous one is moved into `_backup`. The backup is retained for manual rollback or inspection.

If an exception occurs before committing the new manifest:

- newly published output is moved to `_failed`;
- the preceding partition is restored from `_backup` when available;
- the previous completed manifest record is restored, or a `failed` record is written.

No source ZIP is deleted or overwritten by Phase 2.

## Recovery

`--recover` permits the pipeline to quarantine an incomplete or untracked output in `_recovery` before retrying. For an interrupted replacement, the previous backup is restored first.

On a hard process crash, the exclusive `ingestion.lock` may remain. A human must confirm that no ingestion process is active before removing that stale lock; the pipeline does not automatically defeat the lock.

## State and errors

| State | Meaning |
| --- | --- |
| `running` | Conversion began but is not yet committed |
| `completed` | Source and published Parquet passed validation |
| `failed` | The attempted conversion failed; details are recorded |
| `requires_review` (alert) | The current ZIP differs from verified Phase 1 source evidence |

Local artifacts are kept under `data/bronze` and are excluded from Git. Phase 4 will add GitHub Actions CI; Phase 7 will provide scheduled orchestration through Dagster.
