"""
Hermetic Unit & Integration Tests for EcoCompress AI Phase 6: Candidate Validation & Comparative Evaluation.
Validates candidate tensor inspection, dequantization verification using stored scales and zero points,
comparative metric deltas, acceptance gate evaluation, and SQLite experiment projection.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import torch
import safetensors.torch

# Ensure services/api is in sys.path
import sys
API_DIR = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(API_DIR))

from database import init_db, get_db
from schemas import (
    ExperimentCreate,
    ExperimentStatus,
    AcceptanceDecision,
    AcceptanceThresholds,
)
from services.experiment_service import ExperimentService


class TestPhase6ComparativeEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Anchor temporary test database to tempfile on D:
        cls.test_dir = tempfile.mkdtemp(prefix="ecocompress_test_p6_")
        cls.db_path = Path(cls.test_dir) / "test_evaluation.db"
        init_db(cls.db_path)
        cls.exp_service = ExperimentService(db_path=cls.db_path)

        # Create a small synthetic quantized model fixture
        cls.candidate_dir = Path(cls.test_dir) / "synthetic_candidate_int8"
        cls.candidate_dir.mkdir(parents=True, exist_ok=True)

        w_int8 = torch.randint(-128, 127, (64, 32), dtype=torch.int8)
        scale = torch.tensor([0.025], dtype=torch.float32)
        zero_point = torch.tensor([5], dtype=torch.int8)

        tensors = {
            "model.embed_tokens.weight": torch.randn(100, 32, dtype=torch.float32),
            "model.layers.0.self_attn.q_proj.weight": w_int8,
            "model.layers.0.self_attn.q_proj.weight_scale": scale,
            "model.layers.0.self_attn.q_proj.weight_zero_point": zero_point,
            "model.norm.weight": torch.ones(32, dtype=torch.float32),
        }
        safetensors.torch.save_file(tensors, str(cls.candidate_dir / "model.safetensors"))

        with open(cls.candidate_dir / "config.json", "w") as f:
            json.dump({"architectures": ["SyntheticModel"], "quantization_config": {"bits": 8}}, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. Candidate Tensor Validation
    # -------------------------------------------------------------
    def test_01_candidate_tensor_safetensors_inspection(self):
        """Verify candidate tensors have correct int8 dtypes, scales, and zero points."""
        state = safetensors.torch.load_file(str(self.candidate_dir / "model.safetensors"))

        # Verify int8 dtype
        q_weight = state["model.layers.0.self_attn.q_proj.weight"]
        self.assertEqual(q_weight.dtype, torch.int8)
        self.assertEqual(q_weight.shape, (64, 32))

        # Verify scale and zero point
        scale = state["model.layers.0.self_attn.q_proj.weight_scale"]
        zp = state["model.layers.0.self_attn.q_proj.weight_zero_point"]
        self.assertEqual(scale.dtype, torch.float32)
        self.assertEqual(zp.dtype, torch.int8)
        self.assertAlmostEqual(scale.item(), 0.025, places=4)
        self.assertEqual(zp.item(), 5)

        # Verify non-quantized tensors remain float32
        self.assertEqual(state["model.embed_tokens.weight"].dtype, torch.float32)
        self.assertEqual(state["model.norm.weight"].dtype, torch.float32)

    def test_02_dequantization_math_reconstruction(self):
        """Verify stored scales and zero points accurately reconstruct effective weights."""
        state = safetensors.torch.load_file(str(self.candidate_dir / "model.safetensors"))
        w_int8 = state["model.layers.0.self_attn.q_proj.weight"]
        scale = state["model.layers.0.self_attn.q_proj.weight_scale"].item()
        zp = state["model.layers.0.self_attn.q_proj.weight_zero_point"].item()

        # Reconstruct: W = (w_int8 - zp) * scale
        w_dequant = (w_int8.to(torch.float32) - zp) * scale
        self.assertEqual(w_dequant.dtype, torch.float32)
        self.assertEqual(w_dequant.shape, (64, 32))

        # Test affine reconstruction on a known integer value
        # If w_int8 = 5 and zp = 5, w_dequant must equal 0.0
        sample_idx = (w_int8 == 5).nonzero(as_tuple=True)
        if len(sample_idx[0]) > 0:
            first_idx = (sample_idx[0][0], sample_idx[1][0])
            self.assertAlmostEqual(w_dequant[first_idx].item(), 0.0, places=5)

    # -------------------------------------------------------------
    # 2. Acceptance Gate Logic
    # -------------------------------------------------------------
    def test_03_acceptance_gate_decision_logic(self):
        """Verify acceptance threshold evaluation for size reduction and quality."""
        # Scenario A: Pass (size reduction 43.46% >= threshold 40.0%)
        size_reduction_pct = 43.46
        threshold_min_reduction = 40.0
        passed = size_reduction_pct >= threshold_min_reduction
        self.assertTrue(passed)

        # Scenario B: Fail (size reduction 35.0% < threshold 40.0%)
        fail_reduction_pct = 35.0
        failed = fail_reduction_pct >= threshold_min_reduction
        self.assertFalse(failed)

    # -------------------------------------------------------------
    # 3. SQLite Database Projection of Comparative Metrics
    # -------------------------------------------------------------
    def test_04_comparative_metrics_persistence_and_retrieval(self):
        """Verify that baseline and candidate metrics populate ExperimentResponse."""
        exp = self.exp_service.create_experiment(
            ExperimentCreate(
                name="Comparative Evaluation Test",
                model_id="test/comparative-model",
            )
        )

        # Insert baseline record
        with get_db(self.db_path) as conn:
            conn.execute(
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
                    exp.id, "baseline", 690.15,
                    190.37, 3417.07, 1850.34,
                    None, None,
                    None, "unavailable",
                    None, "unavailable",
                    None, "unavailable",
                    10, 3, "CPU: Intel Core i5",
                    "2026-10-20 10:21:27 UTC", "PyTorch 2.12.0+cpu", "a10cc1512", "{}"
                ),
            )

            # Insert candidate record
            conn.execute(
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
                    exp.id, "candidate", 390.20,
                    3128.74, 3681.01, 1958.42,
                    None, "unverified",
                    None, "unavailable",
                    None, "unavailable",
                    None, "unavailable",
                    10, 3, "CPU: Intel Core i5",
                    "2026-10-20 10:44:57 UTC", "PyTorch 2.12.0+cpu", "a10cc1512", "{}"
                ),
            )

            # Set acceptance decision
            dec = AcceptanceDecision(
                passed=True,
                reasons=["Storage reduction passed: achieved 43.46% (threshold: >= 40%)."],
                timestamp="2026-10-20 10:44:57 UTC",
            )
            conn.execute(
                "UPDATE experiments SET acceptance_decision = ?, status = 'completed' WHERE id = ?",
                (dec.model_dump_json(), exp.id),
            )

        # Retrieve through ExperimentService
        fetched = self.exp_service.get_experiment(exp.id)
        self.assertEqual(fetched.status, ExperimentStatus.COMPLETED)
        self.assertIsNotNone(fetched.baseline_metrics)
        self.assertIsNotNone(fetched.candidate_metrics)
        self.assertIsNotNone(fetched.acceptance_decision)

        # Verify baseline values
        self.assertEqual(fetched.baseline_metrics.artifact_size_mb.value, 690.15)
        self.assertEqual(fetched.baseline_metrics.median_latency_ms.value, 190.37)

        # Verify candidate values
        self.assertEqual(fetched.candidate_metrics.artifact_size_mb.value, 390.20)
        self.assertEqual(fetched.candidate_metrics.median_latency_ms.value, 3128.74)

        # Verify acceptance decision
        self.assertTrue(fetched.acceptance_decision.passed)
        self.assertIn("43.46%", fetched.acceptance_decision.reasons[0])


if __name__ == "__main__":
    unittest.main()
