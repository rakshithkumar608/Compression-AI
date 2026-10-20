"""
EcoCompress AI - Baseline Benchmarking Engine (Phase 4)
Reproducible, deterministic benchmark orchestration for model performance and resource consumption.
Implements warmup, timed latency collection (median/P95), memory profiling,
strict measurement integrity, progress reporting, cancellation, and persistence.
"""

import json
import math
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil
import torch

from database import get_db, get_db_path
from schemas import (
    BenchmarkConfigSchema,
    BenchmarkDetailResponse,
    BenchmarkMetric,
    BenchmarkSummary,
    ExperimentStatus,
    LatencyDetailSchema,
    MemoryDetailSchema,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class BenchmarkError(Exception):
    """Base exception for benchmark operations."""
    pass


class BenchmarkConfigError(BenchmarkError):
    """Raised when benchmark configuration is invalid or unsupported by hardware."""
    pass


class BenchmarkCancelledError(BenchmarkError):
    """Raised when benchmark is halted due to a cooperative cancellation request."""
    pass


class BenchmarkExecutionError(BenchmarkError):
    """Raised when benchmark iteration fails during execution."""
    pass


def calculate_latency_statistics(samples_ms: List[float]) -> LatencyDetailSchema:
    """
    Computes rigorous latency statistics for a sequence of millisecond timings.
    Calculates median (50th percentile) and P95 (95th percentile) using deterministic
    rank-based interpolation.
    """
    if not samples_ms:
        raise BenchmarkExecutionError("Cannot calculate latency statistics on empty sample list.")

    n = len(samples_ms)
    sorted_samples = sorted(samples_ms)

    # Median (50th percentile)
    median_val = float(statistics.median(sorted_samples))

    # P95 (95th percentile)
    if n == 1:
        p95_val = sorted_samples[0]
    else:
        # Standard nearest-rank / linear index formula: k = 0.95 * (n - 1)
        rank_idx = 0.95 * (n - 1)
        floor_idx = int(math.floor(rank_idx))
        ceil_idx = int(math.ceil(rank_idx))
        fraction = rank_idx - floor_idx

        if floor_idx == ceil_idx or ceil_idx >= n:
            p95_val = float(sorted_samples[floor_idx])
        else:
            p95_val = float(sorted_samples[floor_idx] + fraction * (sorted_samples[ceil_idx] - sorted_samples[floor_idx]))

    mean_val = float(sum(sorted_samples) / n)
    min_val = float(sorted_samples[0])
    max_val = float(sorted_samples[-1])
    std_dev_val = float(statistics.stdev(sorted_samples)) if n > 1 else 0.0

    return LatencyDetailSchema(
        median_ms=round(median_val, 3),
        p95_ms=round(p95_val, 3),
        mean_ms=round(mean_val, 3),
        min_ms=round(min_val, 3),
        max_ms=round(max_val, 3),
        std_dev_ms=round(std_dev_val, 3),
        sample_count=n,
        raw_samples_ms=[round(s, 3) for s in sorted_samples],
    )


class WorkloadDefinition:
    """
    Standard, reproducible benchmark test workload.
    Guarantees deterministic inputs and consistent prompt lengths across runs.
    """
    FIXED_PROMPTS = [
        "Explain the law of conservation of energy in simple, concise terms for an engineering student.",
        "Summarize three key differences between static quantization and dynamic quantization in deep learning.",
        "Given the following sentence, determine if the sentiment is positive or negative: The latency improved by 40%.",
        "Write a Python function to compute the median and 95th percentile of a list of floating-point numbers.",
        "Explain why measuring peak memory and model file size is critical for edge device deployment.",
    ]

    @classmethod
    def get_standard_workload(cls, task: str = "text-generation") -> Dict[str, Any]:
        return {
            "name": "ecocompress_standard_benchmark_suite_v1",
            "task": task,
            "prompt_count": len(cls.FIXED_PROMPTS),
            "sample_prompts": cls.FIXED_PROMPTS,
            "deterministic_seed": 42,
            "greedy_decoding": True,
            "generation_parameters": {
                "temperature": 0.0,
                "do_sample": False,
                "max_new_tokens": 32,
            },
        }


class BenchmarkEngine:
    """
    Benchmark engine orchestrating repeatable baseline and candidate runs.
    Decoupled from HTTP request lifecycle; safe for background workers or test harnesses.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = get_db_path(db_path)
        self._current_process = psutil.Process()

    def validate_config(self, config: BenchmarkConfigSchema) -> None:
        """Validates that requested configuration can run safely on current hardware."""
        target_dev = config.target_device.lower().strip()
        if target_dev in ["cuda", "gpu", "cuda:0"]:
            if not torch.cuda.is_available():
                raise BenchmarkConfigError(
                    f"Target device '{config.target_device}' was requested, but CUDA is unavailable in the current "
                    f"PyTorch runtime (detected PyTorch build: {torch.__version__}). Use 'cpu' instead."
                )

    def get_runtime_environment(self, target_device: str) -> Dict[str, Any]:
        """Collects verified host runtime and hardware device specifications."""
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        py_ver = f"{platform.python_implementation()} {platform.python_version()}"
        torch_ver = torch.__version__

        if target_device.lower().startswith("cuda") and torch.cuda.is_available():
            device_str = f"GPU: {torch.cuda.get_device_name(0)}"
            cuda_active = True
        else:
            cpu_name = platform.processor() or "x86_64 CPU"
            device_str = f"CPU: {cpu_name} ({cpu_count_physical} cores / {cpu_count_logical} threads)"
            cuda_active = False

        return {
            "device_str": device_str,
            "cuda_active": cuda_active,
            "runtime_name": f"PyTorch {torch_ver} ({py_ver}) / {platform.system()}-{platform.machine()}",
            "logical_cores": cpu_count_logical,
            "physical_cores": cpu_count_physical,
        }

    def measure_memory_sample(self, cuda_active: bool) -> Dict[str, Any]:
        """Measures process RSS memory and GPU memory (if CUDA active)."""
        rss_bytes = self._current_process.memory_info().rss
        rss_mb = round(rss_bytes / (1024 * 1024), 2)

        gpu_mb = None
        if cuda_active and torch.cuda.is_available():
            try:
                gpu_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
            except Exception:
                gpu_mb = None

        return {
            "rss_mb": rss_mb,
            "gpu_mb": gpu_mb,
        }

    def run_synthetic_benchmark(
        self,
        experiment_id: str,
        config: Optional[BenchmarkConfigSchema] = None,
        synthetic_step_fn: Optional[Callable[[int], None]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None,
        artifact_size_mb: Optional[float] = 12.5,
    ) -> BenchmarkDetailResponse:
        """
        Executes a controlled benchmark run using a deterministic synthetic step workload.
        Useful for verification, end-to-end integration tests, and pipeline dry-runs without
        downloading heavy model weights.
        """
        if config is None:
            config = BenchmarkConfigSchema()

        self.validate_config(config)

        # Default synthetic workload: small deterministic matrix multiplication
        if synthetic_step_fn is None:
            def default_synthetic_workload(step_idx: int) -> None:
                # Deterministic math operations
                a = torch.ones((128, 128), dtype=torch.float32)
                b = torch.ones((128, 128), dtype=torch.float32) * (step_idx + 1)
                _ = torch.matmul(a, b)
                # Ensure predictable timing
                time.sleep(0.005)

            synthetic_step_fn = default_synthetic_workload

        return self._execute_benchmark_loop(
            experiment_id=experiment_id,
            candidate_type="baseline",
            model_id="synthetic-benchmark-model",
            model_revision=None,
            artifact_size_mb=artifact_size_mb,
            config=config,
            step_fn=synthetic_step_fn,
            progress_callback=progress_callback,
            cancellation_check=cancellation_check,
            quality_score=None,
            quality_metric_name=None,
            workload_snapshot=WorkloadDefinition.get_standard_workload(),
        )

    def _execute_benchmark_loop(
        self,
        experiment_id: str,
        candidate_type: str,
        model_id: str,
        model_revision: Optional[str],
        artifact_size_mb: Optional[float],
        config: BenchmarkConfigSchema,
        step_fn: Callable[[int], None],
        progress_callback: Optional[Callable[[str, int], None]],
        cancellation_check: Optional[Callable[[], bool]],
        quality_score: Optional[float],
        quality_metric_name: Optional[str],
        workload_snapshot: Dict[str, Any],
    ) -> BenchmarkDetailResponse:
        """
        Core benchmark execution loop.
        Executes warmup runs, timed measurement runs, tracks memory, checks cancellation,
        computes latency statistics, and persists result to database.
        """
        env_info = self.get_runtime_environment(config.target_device)
        cuda_active = env_info["cuda_active"]

        # Track memory baseline before workload starts
        baseline_mem = self.measure_memory_sample(cuda_active)
        baseline_rss_mb = baseline_mem["rss_mb"]
        peak_rss_mb = baseline_rss_mb
        peak_gpu_mb = baseline_mem["gpu_mb"]

        if cuda_active and torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        def check_cancellation():
            # Check programmatic callback if provided
            if cancellation_check and cancellation_check():
                raise BenchmarkCancelledError(f"Benchmark for experiment '{experiment_id}' was cancelled by user request.")
            # Also check database status if db_path is configured
            if self.db_path:
                with get_db(self.db_path) as conn:
                    cur = conn.execute("SELECT status FROM experiments WHERE id = ?", (experiment_id,))
                    row = cur.fetchone()
                    if row and row["status"] == ExperimentStatus.CANCELLED.value:
                        raise BenchmarkCancelledError(f"Benchmark for experiment '{experiment_id}' was cancelled in database.")

        def report_progress(step_desc: str, pct: int):
            if progress_callback:
                progress_callback(step_desc, pct)
            if self.db_path:
                now = _utc_now_iso()
                with get_db(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET current_step = ?, progress_pct = ?, updated_at = ?
                        WHERE experiment_id = ? AND status != 'cancelled'
                        """,
                        (step_desc, pct, now, experiment_id),
                    )

        # Transition experiment to BASELINE_RUNNING if in database
        if self.db_path:
            with get_db(self.db_path) as conn:
                now = _utc_now_iso()
                conn.execute(
                    """
                    UPDATE experiments
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND status != 'cancelled'
                    """,
                    (ExperimentStatus.BASELINE_RUNNING.value, now, experiment_id),
                )

        total_steps = config.warmup_runs + config.measured_runs
        current_step_num = 0

        # --- Phase 1: Warmup ---
        report_progress(f"Starting warmup ({config.warmup_runs} iterations)...", 5)
        for i in range(config.warmup_runs):
            check_cancellation()
            try:
                step_fn(i)
            except Exception as e:
                err_msg = f"Error during warmup iteration {i + 1}: {str(e)}"
                self._record_failure(experiment_id, err_msg)
                raise BenchmarkExecutionError(err_msg) from e

            # Memory tracking
            mem = self.measure_memory_sample(cuda_active)
            if mem["rss_mb"] > peak_rss_mb:
                peak_rss_mb = mem["rss_mb"]

            current_step_num += 1
            progress_pct = 5 + int((current_step_num / total_steps) * 20)  # Warmup covers up to 25%
            report_progress(f"Warmup iteration {i + 1}/{config.warmup_runs}", progress_pct)

        # --- Phase 2: Timed Measurement ---
        report_progress(f"Starting timed measurement ({config.measured_runs} iterations)...", 25)
        latencies_ms: List[float] = []

        start_time_all = time.perf_counter()
        for i in range(config.measured_runs):
            check_cancellation()

            # Monotonic high-resolution timer
            t0 = time.perf_counter_ns()
            try:
                step_fn(i)
            except Exception as e:
                err_msg = f"Error during measured iteration {i + 1}: {str(e)}"
                self._record_failure(experiment_id, err_msg)
                raise BenchmarkExecutionError(err_msg) from e
            t1 = time.perf_counter_ns()

            iteration_latency_ms = (t1 - t0) / 1_000_000.0
            latencies_ms.append(iteration_latency_ms)

            # Memory tracking
            mem = self.measure_memory_sample(cuda_active)
            if mem["rss_mb"] > peak_rss_mb:
                peak_rss_mb = mem["rss_mb"]

            current_step_num += 1
            progress_pct = 25 + int(((i + 1) / config.measured_runs) * 70)  # Measured covers 25% -> 95%
            report_progress(f"Timed run {i + 1}/{config.measured_runs} ({iteration_latency_ms:.2f} ms)", progress_pct)

        # Peak GPU memory check if CUDA was active
        if cuda_active and torch.cuda.is_available():
            try:
                peak_gpu_mb = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2)
            except Exception:
                peak_gpu_mb = None

        latency_stats = calculate_latency_statistics(latencies_ms)
        peak_delta_mb = round(max(0.0, peak_rss_mb - baseline_rss_mb), 2)

        # Limitations list: explicit documentation of constraints
        limitations: List[str] = []
        if not cuda_active:
            limitations.append("Executed on CPU. Hardware GPU was unavailable or PyTorch was built without CUDA support.")
            limitations.append("GPU VRAM measurement unavailable.")
        limitations.append("Energy consumption unavailable: host does not expose an accessible power/RAPL hardware sensor.")
        limitations.append("Carbon footprint unavailable: requires measured energy sensor readings.")
        limitations.append("Water consumption unavailable: no validated local datacenter water-use coefficient.")
        if quality_score is None:
            limitations.append("Quality score unavailable: no ground-truth task validation dataset was evaluated.")

        gpu_notes = "GPU memory tracking active" if cuda_active else "GPU memory tracking unavailable: PyTorch runtime is CPU-only."

        memory_profile = MemoryDetailSchema(
            baseline_rss_mb=baseline_rss_mb,
            peak_rss_mb=peak_rss_mb,
            peak_rss_delta_mb=peak_delta_mb,
            peak_gpu_mb=peak_gpu_mb,
            gpu_device_name=env_info["device_str"] if cuda_active else None,
            measurement_type="measured",
            notes=gpu_notes,
        )

        recorded_at = _utc_now_iso()

        result = BenchmarkDetailResponse(
            experiment_id=experiment_id,
            candidate_type=candidate_type,
            model_id=model_id,
            model_revision=model_revision,
            artifact_size_mb=artifact_size_mb,
            latency=latency_stats,
            memory=memory_profile,
            quality_score=quality_score,
            quality_metric_name=quality_metric_name,
            energy_joules=None,
            energy_measurement_type="unavailable",
            carbon_grams=None,
            carbon_measurement_type="unavailable",
            water_milliliters=None,
            water_measurement_type="unavailable",
            measured_runs=config.measured_runs,
            warmup_runs=config.warmup_runs,
            hardware_device=env_info["device_str"],
            runtime_name=env_info["runtime_name"],
            workload_snapshot=workload_snapshot,
            limitations=limitations,
            notes="Baseline benchmark completed successfully.",
            recorded_at=recorded_at,
        )

        # Persist results in SQLite
        if self.db_path:
            self._persist_result(result)
            report_progress("Benchmark execution completed and persisted.", 100)

        return result

    def _persist_result(self, res: BenchmarkDetailResponse) -> None:
        """Atomically stores benchmark results and updates experiment & job states."""
        with get_db(self.db_path) as conn:
            metadata = {
                "raw_samples_ms": res.latency.raw_samples_ms,
                "workload_snapshot": res.workload_snapshot,
                "limitations": res.limitations,
                "notes": res.notes,
                "memory_profile": res.memory.model_dump(),
            }

            cur = conn.execute(
                """
                INSERT INTO benchmark_results (
                    experiment_id, candidate_type, artifact_size_mb,
                    median_latency_ms, p95_latency_ms, peak_memory_mb,
                    quality_score, quality_metric_name,
                    energy_joules, energy_measurement_type,
                    carbon_grams, carbon_measurement_type,
                    water_milliliters, water_measurement_type,
                    measured_runs, warmup_runs, hardware_device,
                    recorded_at, runtime_name, model_revision, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res.experiment_id,
                    res.candidate_type,
                    res.artifact_size_mb,
                    res.latency.median_ms,
                    res.latency.p95_ms,
                    res.memory.peak_rss_mb,
                    res.quality_score,
                    res.quality_metric_name,
                    res.energy_joules,
                    res.energy_measurement_type,
                    res.carbon_grams,
                    res.carbon_measurement_type,
                    res.water_milliliters,
                    res.water_measurement_type,
                    res.measured_runs,
                    res.warmup_runs,
                    res.hardware_device,
                    res.recorded_at,
                    res.runtime_name,
                    res.model_revision,
                    json.dumps(metadata),
                ),
            )
            res.id = cur.lastrowid

            # Update experiment status to COMPLETED (for baseline evaluation phase)
            conn.execute(
                """
                UPDATE experiments
                SET status = ?, updated_at = ?, completed_at = ?
                WHERE id = ? AND status != 'cancelled'
                """,
                (ExperimentStatus.COMPLETED.value, res.recorded_at, res.recorded_at, res.experiment_id),
            )

            # Update job status
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, current_step = ?, progress_pct = 100, updated_at = ?, completed_at = ?
                WHERE experiment_id = ? AND status != 'cancelled'
                """,
                (ExperimentStatus.COMPLETED.value, "Baseline benchmark completed", res.recorded_at, res.recorded_at, res.experiment_id),
            )

    def _record_failure(self, experiment_id: str, error_message: str) -> None:
        """Marks experiment and job as failed in SQLite."""
        if not self.db_path:
            return
        now = _utc_now_iso()
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                UPDATE experiments
                SET status = ?, error_summary = ?, updated_at = ?, completed_at = ?
                WHERE id = ? AND status != 'cancelled'
                """,
                (ExperimentStatus.FAILED.value, error_message, now, now, experiment_id),
            )
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, updated_at = ?, completed_at = ?
                WHERE experiment_id = ? AND status != 'cancelled'
                """,
                (ExperimentStatus.FAILED.value, error_message, now, now, experiment_id),
            )

    def get_benchmark_detail(self, experiment_id: str, candidate_type: str = "baseline") -> Optional[BenchmarkDetailResponse]:
        """Loads full benchmark detail from SQLite including raw latency distribution."""
        if not self.db_path:
            return None

        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT * FROM benchmark_results
                WHERE experiment_id = ? AND candidate_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (experiment_id, candidate_type),
            )
            row = cur.fetchone()
            if not row:
                return None

            metadata = {}
            if row["metadata_json"]:
                try:
                    metadata = json.loads(row["metadata_json"])
                except Exception:
                    pass

            raw_samples = metadata.get("raw_samples_ms", [])
            workload_snapshot = metadata.get("workload_snapshot", {})
            limitations = metadata.get("limitations", [])
            notes = metadata.get("notes")

            mem_data = metadata.get("memory_profile", {})
            memory_profile = MemoryDetailSchema(
                baseline_rss_mb=mem_data.get("baseline_rss_mb", row["peak_memory_mb"] or 0.0),
                peak_rss_mb=row["peak_memory_mb"] or 0.0,
                peak_rss_delta_mb=mem_data.get("peak_rss_delta_mb", 0.0),
                peak_gpu_mb=mem_data.get("peak_gpu_mb"),
                gpu_device_name=mem_data.get("gpu_device_name"),
                measurement_type="measured",
                notes=mem_data.get("notes"),
            )

            latency_stats = LatencyDetailSchema(
                median_ms=row["median_latency_ms"] or 0.0,
                p95_ms=row["p95_latency_ms"] or 0.0,
                mean_ms=statistics.mean(raw_samples) if raw_samples else (row["median_latency_ms"] or 0.0),
                min_ms=min(raw_samples) if raw_samples else (row["median_latency_ms"] or 0.0),
                max_ms=max(raw_samples) if raw_samples else (row["p95_latency_ms"] or 0.0),
                std_dev_ms=statistics.stdev(raw_samples) if len(raw_samples) > 1 else 0.0,
                sample_count=row["measured_runs"] or len(raw_samples),
                raw_samples_ms=raw_samples,
            )

            return BenchmarkDetailResponse(
                id=row["id"],
                experiment_id=row["experiment_id"],
                candidate_type=row["candidate_type"],
                model_id="inspected-model",
                model_revision=row["model_revision"],
                artifact_size_mb=row["artifact_size_mb"],
                latency=latency_stats,
                memory=memory_profile,
                quality_score=row["quality_score"],
                quality_metric_name=row["quality_metric_name"],
                energy_joules=row["energy_joules"],
                energy_measurement_type=row["energy_measurement_type"] or "unavailable",
                carbon_grams=row["carbon_grams"],
                carbon_measurement_type=row["carbon_measurement_type"] or "unavailable",
                water_milliliters=row["water_milliliters"],
                water_measurement_type=row["water_measurement_type"] or "unavailable",
                measured_runs=row["measured_runs"] or 0,
                warmup_runs=row["warmup_runs"] or 0,
                hardware_device=row["hardware_device"] or "CPU",
                runtime_name=row["runtime_name"] or "PyTorch CPU",
                workload_snapshot=workload_snapshot,
                limitations=limitations,
                notes=notes,
                recorded_at=row["recorded_at"],
            )
