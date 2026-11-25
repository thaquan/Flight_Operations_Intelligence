"""Dagster assets and jobs for the historical BTS warehouse."""

from dagster import (
    AssetExecutionContext,
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    MaterializeResult,
    OpExecutionContext,
    ResourceDefinition,
    RetryPolicy,
    ScheduleDefinition,
    StaticPartitionsDefinition,
    asset,
    define_asset_job,
    in_process_executor,
    job,
    op,
)

from src.phase7.pipeline import MONTHS, PipelineRunner

months = StaticPartitionsDefinition(list(MONTHS))
read_retry = RetryPolicy(max_retries=1, delay=10)


@asset(partitions_def=months, required_resource_keys={"pipeline"},
       retry_policy=read_retry, group_name="flight_ingestion")
def bts_source(context: AssetExecutionContext) -> MaterializeResult:
    """Verify an existing official ZIP against the accepted source manifest."""
    return MaterializeResult(metadata=context.resources.pipeline.verify(context.partition_key))


@asset(partitions_def=months, deps=[bts_source], required_resource_keys={"pipeline"},
       group_name="flight_ingestion")
def bronze_flights(context: AssetExecutionContext) -> MaterializeResult:
    """Run the existing idempotent Bronze writer; never force recovery or replacement."""
    return MaterializeResult(metadata=context.resources.pipeline.run(
        "bronze", context.log, context.partition_key))


@asset(partitions_def=months, deps=[bronze_flights], required_resource_keys={"pipeline"},
       group_name="flight_ingestion")
def silver_flights(context: AssetExecutionContext) -> MaterializeResult:
    """Load and audit a single month using the transactional Silver loader."""
    return MaterializeResult(metadata=context.resources.pipeline.run(
        "silver", context.log, context.partition_key))


@asset(deps=[silver_flights], required_resource_keys={"pipeline"}, group_name="warehouse")
def gold_warehouse(context: AssetExecutionContext) -> MaterializeResult:
    """Reconcile all 24 Silver months before a full dbt build."""
    runner = context.resources.pipeline
    runner.run("silver_reconcile", context.log)
    return MaterializeResult(metadata=runner.run("dbt_build", context.log))


@asset(deps=[gold_warehouse], required_resource_keys={"pipeline"}, group_name="warehouse")
def warehouse_quality(context: AssetExecutionContext) -> MaterializeResult:
    """Run the existing source-to-mart quality gates after dbt succeeds."""
    return MaterializeResult(metadata=context.resources.pipeline.run("quality", context.log))


source_bronze_job = define_asset_job(
    "source_bronze_month", selection=AssetSelection.assets(bts_source, bronze_flights),
    executor_def=in_process_executor,
)
monthly_ingestion_job = define_asset_job(
    "ingest_flight_month", selection=AssetSelection.assets(bts_source, bronze_flights, silver_flights),
    executor_def=in_process_executor,
)
gold_job = define_asset_job(
    "rebuild_gold_and_validate", selection=AssetSelection.assets(gold_warehouse, warehouse_quality),
    executor_def=in_process_executor,
)


@op(required_resource_keys={"pipeline"}, retry_policy=read_retry)
def audit_warehouse(context: OpExecutionContext):
    """Read-only audit, separate from the full-rebuild job."""
    context.resources.pipeline.run("quality", context.log)


@job(executor_def=in_process_executor)
def audit_job():
    audit_warehouse()


weekly_audit = ScheduleDefinition(
    name="weekly_warehouse_audit",
    job=audit_job,
    cron_schedule="0 2 * * 1",
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.STOPPED,
)

defs = Definitions(
    assets=[bts_source, bronze_flights, silver_flights, gold_warehouse, warehouse_quality],
    jobs=[source_bronze_job, monthly_ingestion_job, gold_job, audit_job],
    schedules=[weekly_audit],
    resources={"pipeline": ResourceDefinition.hardcoded_resource(PipelineRunner())},
)
