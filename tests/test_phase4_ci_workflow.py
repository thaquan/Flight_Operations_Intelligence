"""The hosted pipeline must be cheap, deterministic and fixture-only."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_uses_ephemeral_postgres_and_never_loads_raw_data() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "postgres:17" in workflow
    assert "POSTGRES_DB: flight_ci" in workflow
    assert 'FLIGHT_CI_FIXTURE: "1"' in workflow
    assert "python -m src.phase4.ci_fixture setup" in workflow
    assert "python -m src.phase4.ci_fixture verify" in workflow
    assert "dbt build --project-dir dbt --profiles-dir dbt" in workflow
    assert "python -m src.phase4.quality_gates --mode fixture" in workflow
    assert "permissions:\n  contents: read" in workflow
    for forbidden in (
        "src.phase1.download_bts", "src.phase2.ingest",
        "src.phase3.load_silver", "flight_warehouse",
        "data/raw", "data/bronze", "secrets.",
    ):
        assert forbidden not in workflow


def test_ci_seed_has_important_flight_outcome_cases() -> None:
    fixture = (ROOT / "sql/phase4/ci_seed.sql").read_text(encoding="utf-8")
    assert "2024-02-29" in fixture
    assert "on conflict (source_month, source_row_number) do nothing" in fixture.lower()
    assert "repeat('a', 64)" in fixture
    assert "null" in fixture.lower()
    assert "audit.silver_loads" in fixture


def test_full_quality_report_is_read_only_and_versioned() -> None:
    script = (ROOT / "src/phase4/quality_gates.py").read_text(encoding="utf-8")
    assert "phase1/2024_2025/acquisition_manifest.json" in script
    assert "phase3/m32_reconciliation.json" in script
    assert "source_to_fact_monthly_counts" in script
    assert "segment_kpi_reconciliation" in script
