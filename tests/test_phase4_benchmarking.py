"""
Hermetic Unit & Integration Tests for EcoCompress AI Phase 4: Baseline Benchmarking Engine.
Validates benchmark configuration, deterministic latency math (median/P95), peak memory profiling,
measurement integrity (no fabricated numbers), cancellation, error handling, decoupled worker execution,
and SQLite persistence. Uses synthetic test harnesses; downloads zero model weights.
"""

import math
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Ensure services/api is in sys.path
import sys
API_DIR = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(API_DIR))

from main import app
from database import init_db, get_db
from schemas import (
    BenchmarkConfigSchema,
    ExperimentCreate,
    ExperimentStatus,
    LatencyDetailSchema,
)
from services.benchmark_engine import (
    BenchmarkEngine,
    BenchmarkConfigError,
    BenchmarkCancelledError,
    BenchmarkExecutionError,
    calculate_latency_statistics,
    WorkloadDefinition,
)
from services.experiment_service import ExperimentService


class TestPhase4BenchmarkingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Anchor temporary test database strictly to D:\Temp or tempfile
        cls.test_dir = tempfile.mkdtemp(prefix="ecocompress_test_p4_")
        cls.db_path = Path(cls.test_dir) / "test_benchmark.db"
        init_db(cls.db_path)
        cls.engine = BenchmarkEngine(db_path=cls.db_path)
        cls.exp_service = ExperimentService(db_path=cls.db_path)

        import routers.experiments as exp_router
        exp_router.service = cls.exp_service
        exp_router.benchmark_engine = cls.engine

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        # Keep engine and exp_service synced to the test db
        pass

    # -------------------------------------------------------------
    # 1. Benchmark Configuration Validation
    # -------------------------------------------------------------
    def test_01_benchmark_config_validation(self):
        """Verify configuration schema constraints and hardware compatibility validation."""
        # Valid config
        cfg = BenchmarkConfigSchema(warmup_runs=3, measured_runs=10, batch_size=1, target_device="cpu")
        self.assertEqual(cfg.warmup_runs, 3)
        self.assertEqual(cfg.measured_runs, 10)
        self.assertEqual(cfg.target_device, "cpu")

        # Validation against current hardware: CUDA request when CUDA is unavailable must raise BenchmarkConfigError
        with patch("torch.cuda.is_available", return_value=False):
            cuda_cfg = BenchmarkConfigSchema(target_device="cuda")
            with self.assertRaises(BenchmarkConfigError) as ctx:
                self.engine.validate_config(cuda_cfg)
            self.assertIn("CUDA is unavailable", str(ctx.exception))

    # -------------------------------------------------------------
    # 2. Latency Statistics Math (Median, P95, Mean, StdDev)
    # -------------------------------------------------------------
    def test_02_latency_statistics_calculation_odd_and_even(self):
        """Verify deterministic median and P95 calculation on known distributions."""
        # Odd sample count: [10.0, 20.0, 30.0, 40.0, 50.0]
        # Median = 30.0
        # P95: index = 0.95 * 4 = 3.8 -> 40.0 + 0.8 * (50.0 - 40.0) = 48.0
        samples_odd = [50.0, 10.0, 30.0, 20.0, 40.0]
        stats_odd = calculate_latency_statistics(samples_odd)
        self.assertEqual(stats_odd.median_ms, 30.0)
        self.assertEqual(stats_odd.p95_ms, 48.0)
        self.assertEqual(stats_odd.mean_ms, 30.0)
        self.assertEqual(stats_odd.min_ms, 10.0)
        self.assertEqual(stats_odd.max_ms, 50.0)
        self.assertEqual(stats_odd.sample_count, 5)

        # Even sample count: [10.0, 20.0, 30.0, 40.0]
        # Median = (20.0 + 30.0) / 2 = 25.0
        # P95: index = 0.95 * 3 = 2.85 -> 30.0 + 0.85 * (40.0 - 30.0) = 38.5
        samples_even = [40.0, 10.0, 30.0, 20.0]
        stats_even = calculate_latency_statistics(samples_even)
        self.assertEqual(stats_even.median_ms, 25.0)
        self.assertEqual(stats_even.p95_ms, 38.5)
        self.assertEqual(stats_even.sample_count, 4)

    def test_03_latency_statistics_single_sample_and_empty_guard(self):
        """Verify edge cases: single sample and empty list guard."""
        # Single sample: median = p95 = min = max = sample, stddev = 0.0
        stats_single = calculate_latency_statistics([15.5])
        self.assertEqual(stats_single.median_ms, 15.5)
        self.assertEqual(stats_single.p95_ms, 15.5)
        self.assertEqual(stats_single.std_dev_ms, 0.0)
        self.assertEqual(stats_single.sample_count, 1)

        # Empty samples must raise BenchmarkExecutionError
        with self.assertRaises(BenchmarkExecutionError):
            calculate_latency_statistics([])

    # -------------------------------------------------------------
    # 3. Workload Determinism & Reproducibility
    # -------------------------------------------------------------
    def test_04_workload_definition_determinism(self):
        """Verify standard benchmark workload has fixed prompt suite and deterministic seed."""
        w1 = WorkloadDefinition.get_standard_workload("text-generation")
        w2 = WorkloadDefinition.get_standard_workload("text-generation")
        self.assertEqual(w1["name"], "ecocompress_standard_benchmark_suite_v1")
        self.assertEqual(w1["prompt_count"], 5)
        self.assertEqual(w1["deterministic_seed"], 42)
        self.assertEqual(w1["sample_prompts"], w2["sample_prompts"])
        self.assertTrue(w1["greedy_decoding"])

    # -------------------------------------------------------------
    # 4. Synthetic Benchmark Execution & Progress Reporting
    # -------------------------------------------------------------
    def test_05_synthetic_benchmark_execution(self):
        """Verify complete synthetic benchmark loop including warmup, timing, and progress callbacks."""
        # Create a test experiment in SQLite
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Phase 4 Benchmark Test",
                model_id="test/synthetic-model",
            )
        )

        progress_events = []
        def on_progress(step: str, pct: int):
            progress_events.append((step, pct))

        cfg = BenchmarkConfigSchema(warmup_runs=2, measured_runs=5, target_device="cpu")
        res = self.engine.run_synthetic_benchmark(
            experiment_id=exp.id,
            config=cfg,
            progress_callback=on_progress,
        )

        # Verify results
        self.assertEqual(res.experiment_id, exp.id)
        self.assertEqual(res.candidate_type, "baseline")
        self.assertEqual(res.measured_runs, 5)
        self.assertEqual(res.warmup_runs, 2)
        self.assertGreater(res.latency.median_ms, 0.0)
        self.assertGreater(res.latency.p95_ms, 0.0)
        self.assertEqual(res.latency.sample_count, 5)
        self.assertGreaterEqual(res.memory.peak_rss_mb, res.memory.baseline_rss_mb)

        # Verify progress callbacks were fired
        self.assertGreater(len(progress_events), 0)
        # Final progress must reach 100%
        self.assertEqual(progress_events[-1][1], 100)

    # -------------------------------------------------------------
    # 5. Measurement Integrity (No Fabricated Metrics)
    # -------------------------------------------------------------
    def test_06_measurement_integrity_and_unavailable_metrics(self):
        """
        Verify that energy, carbon, water, and unverified quality are reported
        as unavailable (None / 'unavailable'), NEVER silently zeroed or fabricated.
        """
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Integrity Verification Run",
                model_id="test/integrity-model",
            )
        )

        cfg = BenchmarkConfigSchema(warmup_runs=1, measured_runs=3, target_device="cpu")
        res = self.engine.run_synthetic_benchmark(exp.id, config=cfg)

        # Energy must be None and type 'unavailable'
        self.assertIsNone(res.energy_joules)
        self.assertEqual(res.energy_measurement_type, "unavailable")

        # Carbon must be None and type 'unavailable'
        self.assertIsNone(res.carbon_grams)
        self.assertEqual(res.carbon_measurement_type, "unavailable")

        # Water must be None and type 'unavailable'
        self.assertIsNone(res.water_milliliters)
        self.assertEqual(res.water_measurement_type, "unavailable")

        # Quality score must be None for synthetic benchmarks without ground truth
        self.assertIsNone(res.quality_score)

        # Device must be CPU
        self.assertIn("CPU", res.hardware_device)
        self.assertNotIn("GPU", res.hardware_device)

        # Limitations must explicitly document unmeasured aspects
        self.assertTrue(any("CPU" in lim for lim in res.limitations))
        self.assertTrue(any("Energy" in lim for lim in res.limitations))

    # -------------------------------------------------------------
    # 6. Cancellation Support
    # -------------------------------------------------------------
    def test_07_cooperative_cancellation_during_benchmark(self):
        """Verify benchmark halts cleanly when cancelled between iterations."""
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Cancellation Test Run",
                model_id="test/cancel-model",
            )
        )

        iteration_count = [0]
        def step_fn(idx: int):
            iteration_count[0] += 1
            time.sleep(0.01)

        # Callback that requests cancellation after 3 iterations
        def cancel_check() -> bool:
            return iteration_count[0] >= 3

        cfg = BenchmarkConfigSchema(warmup_runs=2, measured_runs=10, target_device="cpu")

        with self.assertRaises(BenchmarkCancelledError):
            self.engine.run_synthetic_benchmark(
                experiment_id=exp.id,
                config=cfg,
                synthetic_step_fn=step_fn,
                cancellation_check=cancel_check,
            )

        # Iterations must have stopped early (around 3 or 4 iterations, far fewer than 12)
        self.assertLess(iteration_count[0], 6)

    # -------------------------------------------------------------
    # 7. Error Handling & Failure State Recording
    # -------------------------------------------------------------
    def test_08_error_handling_marks_experiment_failed(self):
        """Verify runtime error in benchmark loop is caught, recorded, and marks experiment as FAILED."""
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Error Handling Test Run",
                model_id="test/error-model",
            )
        )

        def failing_step_fn(idx: int):
            if idx == 1:
                raise RuntimeError("Simulated OOM or runtime tensor execution fault.")

        cfg = BenchmarkConfigSchema(warmup_runs=2, measured_runs=5, target_device="cpu")

        with self.assertRaises(BenchmarkExecutionError):
            self.engine.run_synthetic_benchmark(
                experiment_id=exp.id,
                config=cfg,
                synthetic_step_fn=failing_step_fn,
            )

        # Verify database record transitioned to FAILED with error summary
        updated_exp = self.exp_service.get_experiment(exp.id)
        self.assertEqual(updated_exp.status, ExperimentStatus.FAILED)
        self.assertIn("Simulated OOM", updated_exp.error_summary)

    # -------------------------------------------------------------
    # 8. Persistence to SQLite and Retrieval via API
    # -------------------------------------------------------------
    def test_09_persistence_and_experiment_response_integration(self):
        """Verify benchmark results are persisted in SQLite and populated in ExperimentResponse."""
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Persistence Integration Run",
                model_id="test/persist-model",
            )
        )

        cfg = BenchmarkConfigSchema(warmup_runs=1, measured_runs=4, target_device="cpu")
        res = self.engine.run_synthetic_benchmark(exp.id, config=cfg)

        # 1. Verify through experiment_service.get_experiment
        fetched = self.exp_service.get_experiment(exp.id)
        self.assertEqual(fetched.status, ExperimentStatus.COMPLETED)
        self.assertIsNotNone(fetched.baseline_metrics)
        self.assertEqual(fetched.baseline_metrics.median_latency_ms.value, res.latency.median_ms)
        self.assertEqual(fetched.baseline_metrics.p95_latency_ms.value, res.latency.p95_ms)
        self.assertEqual(fetched.baseline_metrics.median_latency_ms.unit, "ms")
        self.assertEqual(fetched.baseline_metrics.median_latency_ms.type, "measured")
        self.assertIsNone(fetched.baseline_metrics.energy_joules.value)
        self.assertEqual(fetched.baseline_metrics.energy_joules.type, "unavailable")

        # 2. Verify through engine.get_benchmark_detail
        detail = self.engine.get_benchmark_detail(exp.id, candidate_type="baseline")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.latency.median_ms, res.latency.median_ms)
        self.assertEqual(len(detail.latency.raw_samples_ms), 4)

    # -------------------------------------------------------------
    # 9. HTTP REST Endpoints Integration
    # -------------------------------------------------------------
    def test_10_api_endpoints_synthetic_benchmark_and_get_detail(self):
        """Verify POST /experiments/{id}/benchmark/synthetic and GET /experiments/{id}/benchmark."""
        # 1. Create experiment via API
        post_resp = self.client.post(
            "/experiments",
            json={
                "name": "API Benchmark Endpoint Test",
                "model_id": "test/api-benchmark-model",
            },
        )
        self.assertEqual(post_resp.status_code, 201)
        exp_id = post_resp.json()["id"]

        # 2. Run synthetic benchmark via POST endpoint
        bench_resp = self.client.post(
            f"/experiments/{exp_id}/benchmark/synthetic",
            json={
                "warmup_runs": 2,
                "measured_runs": 4,
                "target_device": "cpu",
            },
        )
        self.assertEqual(bench_resp.status_code, 200)
        data = bench_resp.json()
        self.assertEqual(data["experiment_id"], exp_id)
        self.assertIn("median_ms", data["latency"])
        self.assertIn("peak_rss_mb", data["memory"])

        # 3. Retrieve benchmark detail via GET endpoint
        get_bench = self.client.get(f"/experiments/{exp_id}/benchmark")
        self.assertEqual(get_bench.status_code, 200)
        detail = get_bench.json()
        self.assertEqual(detail["experiment_id"], exp_id)
        self.assertEqual(detail["latency"]["sample_count"], 4)

        # 4. Check 404 for nonexistent experiment
        err_bench = self.client.get("/experiments/exp-nonexistent-999/benchmark")
        self.assertEqual(err_bench.status_code, 404)


if __name__ == "__main__":
    unittest.main()
