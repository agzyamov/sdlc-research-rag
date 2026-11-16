"""Dagster code location for the corpus pipeline.

UI, daily schedule and automation:
    DAGSTER_HOME=$PWD/.dagster uv run dagster dev -m sdlcrag.orchestration.definitions -p 3070
"""

import dagster as dg

from sdlcrag.orchestration.assets import (
    SyncConfig,
    corpus_plan,
    entity_resolution,
    paper_facts,
    paper_index,
)

daily_update_job = dg.define_asset_job(
    "daily_update",
    selection=[corpus_plan],
    config=dg.RunConfig(ops={"corpus_plan": SyncConfig(incremental=True)}),
)

defs = dg.Definitions(
    assets=[corpus_plan, paper_index, paper_facts, entity_resolution],
    jobs=[daily_update_job],
    schedules=[
        # New papers are then indexed and extracted by the assets' eager automation.
        dg.ScheduleDefinition(job=daily_update_job, cron_schedule="0 6 * * *")
    ],
)
