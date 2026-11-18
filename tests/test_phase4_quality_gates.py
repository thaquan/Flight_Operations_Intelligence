"""Offline unit tests for Phase 4 gate logic and fixture safety."""

from __future__ import annotations

import pytest

from src.phase4.ci_fixture import EXPECTED_MONTHLY_ROWS, require_fixture_environment
from src.phase4.quality_gates import METRICS, as_monthly, evaluate


def inputs() -> dict:
    network = {
        "2024-01": (6, 4, 1, 1, 3, 2, 1),
        "2024-02": (2, 2, 0, 0, 2, 1, 1),
        "2025-01": (2, 1, 1, 0, 1, 0, 1),
    }
    fact = dict(EXPECTED_MONTHLY_ROWS)
    silver = dict(EXPECTED_MONTHLY_ROWS)
    audit = {
        month: ("a" * 64, count, count)
        for month, count in EXPECTED_MONTHLY_ROWS.items()
    }
    segments = [
        (role, month, *values)
        for role in ("airline", "route", "origin", "destination")
        for month, values in network.items()
    ]
    return {
        "network": network, "fact": fact, "silver": silver,
        "audit": audit, "segment_rows": segments,
        "expected_months": set(network),
        "profile": None, "manifest": None, "baseline_monthly": None,
    }


def test_healthy_fixture_passes_every_gate() -> None:
    report = evaluate(**inputs())
    assert report["status"] == "PASS"
    assert report["summary"]["FAIL"] == 0
    assert report["totals"]["scheduled_flights"] == 10
    assert report["totals"]["eligible_arrivals"] == 6
    assert set(report["totals"]) == set(METRICS)


@pytest.mark.parametrize("damage", [
    "missing_month", "fact_drift", "audit_drift", "route_drift",
    "bad_arrival_denominator", "source_hash_drift",
])
def test_broken_inputs_fail_closed(damage: str) -> None:
    data = inputs()
    if damage == "missing_month":
        data["network"].pop("2024-02")
    elif damage == "fact_drift":
        data["fact"]["2024-01"] += 1
    elif damage == "audit_drift":
        data["audit"]["2024-01"] = ("a" * 64, 6, 5)
    elif damage == "route_drift":
        data["segment_rows"] = [
            (role, month, *(values if (role, month) != ("route", "2024-01")
                            else (5, *values[1:])))
            for role, month, *values in data["segment_rows"]
        ]
    elif damage == "bad_arrival_denominator":
        data["network"]["2024-02"] = (2, 2, 0, 0, 1, 1, 1)
    elif damage == "source_hash_drift":
        data["manifest"] = {
            month: "b" * 64 for month in EXPECTED_MONTHLY_ROWS
        }
    report = evaluate(**data)
    assert report["status"] == "FAIL"
    assert report["summary"]["FAIL"] > 0


def test_profile_exceptions_remain_review_not_failure() -> None:
    data = inputs()
    totals = {key: sum(row[index] for row in data["network"].values())
              for index, key in enumerate(METRICS)}
    profile_map = {
        "scheduled_flights": "scheduled_flights",
        "completed_flights": "completed_flights",
        "cancelled_flights": "cancelled_flights",
        "diverted_not_cancelled_flights": "diverted_flights",
        "arrival_delay15_eligible_flights": "eligible_arrivals",
        "arrival_delayed_15min": "late_arrivals_15",
        "on_time_arrivals": "on_time_arrivals",
    }
    data["profile"] = {
        "overall": {source: totals[metric] for source, metric in profile_map.items()},
        "checks": {"warnings": ["Known late-arrival denominator exception"]},
    }
    report = evaluate(**data)
    assert report["status"] == "REVIEW"
    assert report["summary"]["REVIEW"] == 1
    assert report["summary"]["FAIL"] == 0


def test_month_loader_rejects_duplicate_months() -> None:
    with pytest.raises(ValueError, match="Duplicate month"):
        as_monthly([("2024-01", 1), ("2024-01", 2)])


def test_ci_fixture_refuses_production_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLIGHT_CI_FIXTURE", "1")
    monkeypatch.setenv("POSTGRES_DB", "flight_warehouse")
    with pytest.raises(RuntimeError, match="flight_ci"):
        require_fixture_environment()
    monkeypatch.setenv("POSTGRES_DB", "flight_ci")
    monkeypatch.delenv("FLIGHT_CI_FIXTURE")
    with pytest.raises(RuntimeError, match="FLIGHT_CI_FIXTURE"):
        require_fixture_environment()
