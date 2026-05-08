from datetime import datetime, timezone

from extractor.audit import AuditStore, RunStageState
from extractor.contracts import (
    PlanningRefusal,
    RunManifest,
    SchemaSelectionPolicy,
)


STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


def make_refusal() -> PlanningRefusal:
    return PlanningRefusal(
        run_id="run-1",
        doc_id="doc-1",
        document_class="financial_update",
        domain_hints=("finance",),
        policy=SchemaSelectionPolicy(
            require_approved_schema=True,
            minimum_schema_coverage=0.65,
            allow_planner_generated_fallback=False,
        ),
        candidate_schema_ids=(),
        fit_assessments=(),
        reason_codes=("no_approved_schema_candidates",),
    )


def make_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="running",
        started_at=STARTED,
        output_data_point_ids=(),
    )


def test_audit_stage_state_round_trips_planner_refusal_payload(tmp_path):
    async def run_check() -> None:
        state = RunStageState(
            run_id="run-1",
            stage="planner",
            completed_at=STARTED,
            planning_refusal=make_refusal(),
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_run_manifest(make_manifest())
            await store.record_run_stage_state(state)

            assert await store.get_run_stage_state("run-1", "planner") == state

    import asyncio

    asyncio.run(run_check())
