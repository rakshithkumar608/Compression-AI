"""
Experiment Domain Service for EcoCompress AI.
Handles creation, retrieval, validation, lifecycle state transitions, and cancellation.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path

from database import get_db
from schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentSummaryItem,
    ExperimentListResponse,
    ExperimentStatus,
    VALID_TRANSITIONS,
    AcceptanceDecision,
    JobStatusResponse,
    WorkloadConfig,
    AcceptanceThresholds,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class ExperimentNotFoundError(Exception):
    pass


class InvalidStateTransitionError(Exception):
    pass


class ExperimentService:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = db_path

    def create_experiment(self, payload: ExperimentCreate) -> ExperimentResponse:
        """Creates a new experiment record in the database."""
        now = _utc_now_iso()
        exp_id = f"exp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        workload_json = payload.workload_config.model_dump_json()
        thresholds_json = payload.thresholds.model_dump_json()

        with get_db(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO experiments (
                    id, name, model_id, task, optimization_method,
                    workload_config, thresholds, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exp_id,
                    payload.name,
                    payload.model_id,
                    payload.task.value,
                    payload.optimization_method.value,
                    workload_json,
                    thresholds_json,
                    ExperimentStatus.CREATED.value,
                    now,
                    now,
                ),
            )

        return self.get_experiment(exp_id)

    def get_experiment(self, exp_id: str) -> ExperimentResponse:
        """Retrieves an experiment by ID with full metadata."""
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
            row = cur.fetchone()

            if not row:
                raise ExperimentNotFoundError(f"Experiment '{exp_id}' not found.")

            # Load any attached benchmark results
            # (Phase 2 includes schema support for results)
            return self._row_to_response(row)

    def list_experiments(self, limit: int = 50, offset: int = 0) -> ExperimentListResponse:
        """Returns paginated summaries of experiments."""
        with get_db(self.db_path) as conn:
            total_cur = conn.execute("SELECT COUNT(*) as count FROM experiments")
            total = total_cur.fetchone()["count"]

            cur = conn.execute(
                """
                SELECT id, name, model_id, task, optimization_method, status,
                       created_at, updated_at, acceptance_decision
                FROM experiments
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cur.fetchall()

            items: List[ExperimentSummaryItem] = []
            for r in rows:
                passed = None
                if r["acceptance_decision"]:
                    try:
                        dec = json.loads(r["acceptance_decision"])
                        passed = dec.get("passed")
                    except Exception:
                        pass

                items.append(
                    ExperimentSummaryItem(
                        id=r["id"],
                        name=r["name"],
                        model_id=r["model_id"],
                        task=r["task"],
                        optimization_method=r["optimization_method"],
                        status=ExperimentStatus(r["status"]),
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        passed=passed,
                    )
                )

            return ExperimentListResponse(total=total, experiments=items)

    def transition_status(
        self,
        exp_id: str,
        new_status: ExperimentStatus,
        error_summary: Optional[str] = None,
        acceptance_decision: Optional[AcceptanceDecision] = None,
    ) -> ExperimentResponse:
        """
        Transitions an experiment status using strict state machine validation.
        Prevents invalid transitions or arbitrary status jumps.
        """
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT status FROM experiments WHERE id = ?", (exp_id,))
            row = cur.fetchone()
            if not row:
                raise ExperimentNotFoundError(f"Experiment '{exp_id}' not found.")

            current_status = ExperimentStatus(row["status"])

            # Check validity in transition graph
            allowed = VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                raise InvalidStateTransitionError(
                    f"Invalid lifecycle transition: Cannot move experiment '{exp_id}' "
                    f"from '{current_status.value}' to '{new_status.value}'. "
                    f"Allowed transitions from '{current_status.value}': {[s.value for s in allowed]}"
                )

            now = _utc_now_iso()
            started_at = None
            completed_at = None

            if new_status == ExperimentStatus.QUEUED:
                started_at = now
            elif new_status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED]:
                completed_at = now

            dec_json = acceptance_decision.model_dump_json() if acceptance_decision else None

            conn.execute(
                """
                UPDATE experiments
                SET status = ?,
                    updated_at = ?,
                    started_at = COALESCE(started_at, ?),
                    completed_at = COALESCE(completed_at, ?),
                    error_summary = COALESCE(?, error_summary),
                    acceptance_decision = COALESCE(?, acceptance_decision)
                WHERE id = ?
                """,
                (new_status.value, now, started_at, completed_at, error_summary, dec_json, exp_id),
            )

        return self.get_experiment(exp_id)

    def cancel_experiment(self, exp_id: str, reason: str = "Cancelled by user request") -> ExperimentResponse:
        """
        Cancels an eligible active experiment.
        Terminal states (completed, failed, already cancelled) cannot be cancelled.
        """
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT status FROM experiments WHERE id = ?", (exp_id,))
            row = cur.fetchone()
            if not row:
                raise ExperimentNotFoundError(f"Experiment '{exp_id}' not found.")

            current_status = ExperimentStatus(row["status"])
            if current_status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED]:
                raise InvalidStateTransitionError(
                    f"Cannot cancel experiment '{exp_id}': Experiment is already in terminal state '{current_status.value}'."
                )

        return self.transition_status(
            exp_id=exp_id,
            new_status=ExperimentStatus.CANCELLED,
            error_summary=reason,
        )

    def enqueue_job(self, exp_id: str) -> JobStatusResponse:
        """
        Enqueues an experiment for execution and transitions it to QUEUED.
        Creates an entry in the jobs queue table.
        """
        exp = self.get_experiment(exp_id)
        if exp.status != ExperimentStatus.CREATED:
            raise InvalidStateTransitionError(
                f"Cannot enqueue experiment '{exp_id}': Current status is '{exp.status.value}', expected 'created'."
            )

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        now = _utc_now_iso()

        with get_db(self.db_path) as conn:
            # 1. Transition experiment to QUEUED
            self.transition_status(exp_id, ExperimentStatus.QUEUED)

            # 2. Insert into jobs table
            conn.execute(
                """
                INSERT INTO jobs (
                    id, experiment_id, status, current_step, progress_pct,
                    created_at, updated_at, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    exp_id,
                    ExperimentStatus.QUEUED.value,
                    "Enqueued in execution queue",
                    0,
                    now,
                    now,
                    now,
                ),
            )

        return JobStatusResponse(
            id=job_id,
            experiment_id=exp_id,
            status=ExperimentStatus.QUEUED,
            current_step="Enqueued in execution queue",
            progress_pct=0,
            created_at=now,
            updated_at=now,
        )

    def _row_to_response(self, row) -> ExperimentResponse:
        workload_dict = json.loads(row["workload_config"])
        thresholds_dict = json.loads(row["thresholds"])

        dec = None
        if row["acceptance_decision"]:
            try:
                dec = AcceptanceDecision(**json.loads(row["acceptance_decision"]))
            except Exception:
                pass

        return ExperimentResponse(
            id=row["id"],
            name=row["name"],
            model_id=row["model_id"],
            task=row["task"],
            optimization_method=row["optimization_method"],
            workload_config=WorkloadConfig(**workload_dict),
            thresholds=AcceptanceThresholds(**thresholds_dict),
            status=ExperimentStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            error_summary=row["error_summary"],
            acceptance_decision=dec,
        )
