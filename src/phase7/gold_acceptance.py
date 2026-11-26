"""Run the existing full Gold job against a prepared, isolated Silver snapshot only."""

import json
import os

from src.phase3.config import read_env
from src.phase7.pipeline import ROOT, PipelineRunner

WORKSPACE = ROOT / "data/tmp/m75-gold"


def acceptance_settings():
    settings = read_env(WORKSPACE / ".env")
    if (settings["POSTGRES_DB"], settings["POSTGRES_PORT"]) != ("flight_m75_acceptance", "5543"):
        raise RuntimeError("Gold acceptance requires the dedicated snapshot database on port 5543")
    return settings


def main():
    from dagster import DagsterInstance, ResourceDefinition

    from src.phase7.definitions import defs

    acceptance_settings()
    home = WORKSPACE / "dagster-home"
    if not (home / "dagster.yaml").is_file():
        raise RuntimeError("Prepare the dedicated Dagster instance before acceptance")
    if not (WORKSPACE / "data/bronze/_metadata/ingestion_manifest.json").is_file():
        raise RuntimeError("Full Bronze manifest is required")
    if not (WORKSPACE / "dbt/dbt_project.yml").is_file():
        raise RuntimeError("Copy the versioned dbt project into the isolated workspace")
    python = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    runner = PipelineRunner(WORKSPACE, python)
    with DagsterInstance.from_config(str(home)) as instance:
        if any(not r.is_finished for r in instance.get_runs()):
            raise RuntimeError("Another isolated acceptance run is active")
        result = defs.resolve_job_def("rebuild_gold_and_validate").execute_in_process(
            instance=instance,
            resources={"pipeline": ResourceDefinition.hardcoded_resource(runner)},
            raise_on_error=False,
            tags={"acceptance": "M7.5", "scope": "isolated_full_snapshot"},
        )
        print(json.dumps({"run_id": result.run_id, "success": result.success,
                          "assets": [str(e.asset_key) for e in result.get_asset_materialization_events()]}),
              flush=True)
        if not result.success:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
