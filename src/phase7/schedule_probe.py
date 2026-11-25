"""Isolated, read-only scheduler acceptance code location (not production defs)."""

import os
from pathlib import Path

from dagster import DefaultScheduleStatus, Definitions, ScheduleDefinition, job, op

from src.phase7.pipeline import ROOT, verify_source

HOME = ROOT / "data/tmp/m74-schedule/dagster-home"


@op
def verify_isolated_source(context):
    if Path(os.environ.get("DAGSTER_HOME", ".")).resolve() != HOME.resolve():
        raise RuntimeError("Schedule probe requires its dedicated local instance")
    metadata = verify_source("2024-01", ROOT / "data/tmp/m73-isolated")
    context.log.info("Verified isolated source: %s", metadata)
    return metadata


@job
def scheduled_source_probe():
    verify_isolated_source()


probe_schedule = ScheduleDefinition(
    name="isolated_minute_probe",
    job=scheduled_source_probe,
    cron_schedule="* * * * *",
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.STOPPED,
)

defs = Definitions(jobs=[scheduled_source_probe], schedules=[probe_schedule])
