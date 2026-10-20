"""
Comprehensive Unit & Integration Test Suite for EcoCompress AI Phase 2.
Tests API contracts, SQLite persistence, lifecycle state transitions, input sanitization, and cancellation.
Uses an isolated temporary SQLite database to protect the development database.
"""

import sys
import os
import unittest
import tempfile
from pathlib import Path

# Add services/api to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "api")))

from fastapi.testclient import TestClient
from main import app
from database import init_db
from services.experiment_service import ExperimentService, InvalidStateTransitionError
from schemas import ExperimentCreate, TaskType, OptimizationType, ExperimentStatus, WorkloadConfig, AcceptanceThresholds


class TestEcoCompressApiPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary SQLite database file for testing
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_ecocompress.db"
        
        # Initialize test schema
        init_db(cls.test_db_path)
        cls.service = ExperimentService(db_path=cls.test_db_path)
        
        # Override dependency in router to use test db
        import routers.experiments as exp_router
        exp_router.service = cls.service
        
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_01_health_endpoint(self):
        """Verify health endpoint reports Phase 2 readiness."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("Phase 2", data["phase"])

    def test_02_system_diagnostics_endpoint(self):
        """Verify hardware telemetry endpoint."""
        res = self.client.get("/system")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("os", data)
        self.assertEqual(data["gpu_profile"]["vram_mb"], 4096)

    def test_03_create_experiment_success(self):
        """Verify valid experiment creation and initial status."""
        payload = {
            "name": "DistilBERT SST-2 INT8 Test",
            "model_id": "distilbert-base-uncased",
            "task": "text-classification",
            "optimization_method": "onnx-dynamic-int8",
            "workload_config": {
                "task": "text-classification",
                "dataset": "SST-2 Test Split",
                "sample_count": 250,
                "batch_size": 1,
                "sequence_length": 128,
                "warmup_runs": 5,
                "measured_runs": 25,
            },
            "thresholds": {
                "max_quality_loss_pct": 2.5,
                "min_size_reduction_pct": 50.0,
                "max_latency_increase_pct": 0.0,
            },
        }

        res = self.client.post("/experiments", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["id"].startswith("exp-"))
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["name"], payload["name"])
        self.assertEqual(data["model_id"], payload["model_id"])
        self.assertEqual(data["workload_config"]["sample_count"], 250)
        self.assertEqual(data["thresholds"]["min_size_reduction_pct"], 50.0)

    def test_04_create_experiment_validation_error_unsafe_path(self):
        """Verify security guardrail against path traversal sequences in model_id."""
        payload = {
            "name": "Malicious Path Test",
            "model_id": "../../etc/shadow",
            "task": "text-classification",
            "optimization_method": "onnx-dynamic-int8",
        }
        res = self.client.post("/experiments", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertIn("path traversal", res.json()["detail"].lower())

    def test_05_create_experiment_validation_error_forbidden_chars(self):
        """Verify security guardrail against shell command injection chars in model_id."""
        payload = {
            "name": "Injection Test",
            "model_id": "model; rm -rf /",
            "task": "text-classification",
            "optimization_method": "onnx-dynamic-int8",
        }
        res = self.client.post("/experiments", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertIn("forbidden special characters", res.json()["detail"].lower())

    def test_06_get_experiment_by_id(self):
        """Verify retrieval of an existing experiment."""
        # Create one first
        created = self.service.create_experiment(
            ExperimentCreate(
                name="Retrieval Test Exp",
                model_id="roberta-base",
                task=TaskType.TEXT_CLASSIFICATION,
                optimization_method=OptimizationType.TORCH_DYNAMIC_INT8,
            )
        )

        res = self.client.get(f"/experiments/{created.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], created.id)
        self.assertEqual(data["name"], "Retrieval Test Exp")
        self.assertEqual(data["status"], "created")

    def test_07_get_experiment_404_not_found(self):
        """Verify 404 response for nonexistent experiment ID."""
        res = self.client.get("/experiments/exp-nonexistent-id")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_08_list_experiments(self):
        """Verify experiment listing with pagination."""
        res = self.client.get("/experiments?limit=10&offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 2)
        self.assertIsInstance(data["experiments"], list)

    def test_09_enqueue_and_run_experiment(self):
        """Verify enqueuing experiment into background job queue."""
        exp = self.service.create_experiment(
            ExperimentCreate(
                name="Job Enqueue Test",
                model_id="Qwen/Qwen2.5-0.5B",
                task=TaskType.TEXT_GENERATION,
                optimization_method=OptimizationType.ONNX_DYNAMIC_INT8,
            )
        )

        res = self.client.post(f"/experiments/{exp.id}/run")
        self.assertEqual(res.status_code, 202)
        job = res.json()
        self.assertEqual(job["experiment_id"], exp.id)
        self.assertEqual(job["status"], "queued")

        # Verify experiment status updated in database
        updated_exp = self.service.get_experiment(exp.id)
        self.assertEqual(updated_exp.status, ExperimentStatus.QUEUED)
        self.assertIsNotNone(updated_exp.started_at)

    def test_10_cancel_active_experiment(self):
        """Verify cancelling an active experiment."""
        exp = self.service.create_experiment(
            ExperimentCreate(
                name="Cancellation Test",
                model_id="distilbert-base-uncased",
                task=TaskType.TEXT_CLASSIFICATION,
                optimization_method=OptimizationType.TORCH_DYNAMIC_INT8,
            )
        )

        res = self.client.post(f"/experiments/{exp.id}/cancel")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "cancelled")
        self.assertIsNotNone(data["completed_at"])

    def test_11_reject_invalid_state_transition(self):
        """Verify that illegal status transitions raise InvalidStateTransitionError and HTTP 409."""
        exp = self.service.create_experiment(
            ExperimentCreate(
                name="Illegal Transition Test",
                model_id="distilbert-base-uncased",
                task=TaskType.TEXT_CLASSIFICATION,
                optimization_method=OptimizationType.ONNX_DYNAMIC_INT8,
            )
        )

        # Attempt to jump straight from 'created' to 'completed' (illegal transition)
        with self.assertRaises(InvalidStateTransitionError):
            self.service.transition_status(exp.id, ExperimentStatus.COMPLETED)

        # Enqueue once (moves created -> queued)
        self.service.enqueue_job(exp.id)

        # Attempt to enqueue again (queued -> queued is illegal)
        res = self.client.post(f"/experiments/{exp.id}/run")
        self.assertEqual(res.status_code, 409)

    def test_12_cannot_cancel_already_cancelled_or_completed_experiment(self):
        """Verify terminal state protection against redundant cancellation."""
        exp = self.service.create_experiment(
            ExperimentCreate(
                name="Double Cancel Test",
                model_id="distilbert-base-uncased",
                task=TaskType.TEXT_CLASSIFICATION,
                optimization_method=OptimizationType.ONNX_DYNAMIC_INT8,
            )
        )

        # Cancel once
        self.service.cancel_experiment(exp.id)

        # Cancel again (should fail with 409)
        res = self.client.post(f"/experiments/{exp.id}/cancel")
        self.assertEqual(res.status_code, 409)
        self.assertIn("terminal state", res.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
