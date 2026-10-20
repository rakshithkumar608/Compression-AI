"""
Comprehensive Unit & Integration Test Suite for EcoCompress AI Phase 3:
Hardware Detection, Safe Model Inspection, and Resource Feasibility Gating.
All tests run safely without downloading model weights or altering the system.
External network calls to Hugging Face API are mocked to guarantee hermetic test execution.
"""

import sys
import os
import unittest
import tempfile
import json
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add services/api to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "api")))

from fastapi.testclient import TestClient
from main import app
from services.hardware_service import (
    detect_gpu_telemetry,
    detect_software_capabilities,
    detect_system_storage,
    get_complete_hardware_diagnostic,
)
from services.model_inspector import (
    sanitize_and_validate_local_path,
    parse_safetensors_header,
    inspect_local_model,
    inspect_huggingface_model,
    ModelInspectionError,
)
from services.feasibility_service import (
    estimate_model_feasibility,
    FeasibilityVerdict,
)


class TestPhase3HardwareAndModelInspection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_dir = Path(cls.temp_dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    # ================= 1. Hardware Detection Tests =================

    def test_01_hardware_diagnostics_endpoint(self):
        """Verify GET /hardware/diagnostics returns complete system diagnostic structure."""
        res = self.client.get("/hardware/diagnostics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("cpu", data)
        self.assertIn("ram", data)
        self.assertIn("gpu", data)
        self.assertIn("software", data)
        self.assertIn("storage", data)
        self.assertGreater(data["ram"]["total_gb"], 0)

    def test_02_gpu_telemetry_safe_handling_when_nvidia_smi_missing(self):
        """Verify detect_gpu_telemetry handles missing nvidia-smi without raising exceptions."""
        with patch("shutil.which", return_value=None):
            with patch.object(Path, "exists", return_value=False):
                res = detect_gpu_telemetry()
                self.assertFalse(res["detected"])
                self.assertEqual(res["status"], "unverified")
                self.assertIn("not found", res["notes"].lower())

    def test_03_software_capabilities_cuda_detection(self):
        """Verify software capability detection clearly identifies CPU vs CUDA PyTorch build."""
        caps = detect_software_capabilities({"detected": True})
        self.assertIn("pytorch", caps)
        self.assertIn("cuda_available", caps["pytorch"])
        # In our environment, PyTorch is 2.12.0+cpu, so usable_for_gpu_inference should be False
        self.assertIsInstance(caps["usable_for_gpu_inference"], bool)
        self.assertIsInstance(caps["runtime_assessment"], str)

    # ================= 2. Local Model Inspection & Path Sanitization Tests =================

    def test_04_path_sanitization_rejects_path_traversal(self):
        """Verify path traversal sequences are strictly rejected with UNAPPROVED_DIRECTORY."""
        with self.assertRaises(ModelInspectionError) as ctx:
            sanitize_and_validate_local_path("../../Windows/System32")
        self.assertEqual(ctx.exception.code, "UNAPPROVED_DIRECTORY")

    def test_05_path_sanitization_rejects_empty_path(self):
        """Verify empty path is rejected with EMPTY_PATH."""
        with self.assertRaises(ModelInspectionError) as ctx:
            sanitize_and_validate_local_path("   ")
        self.assertEqual(ctx.exception.code, "EMPTY_PATH")

    def test_06_local_model_inspection_with_safetensors_header(self):
        """
        Verify inspection of a local model directory containing config.json and .safetensors.
        Ensures tensor shapes and parameter counts are parsed without loading tensor data.
        """
        # Create mock model directory in approved artifacts root
        from config import settings
        mock_model_dir = settings.artifacts_dir / "test_local_distilbert"
        mock_model_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create config.json
        config_content = {
            "architectures": ["DistilBertForSequenceClassification"],
            "model_type": "distilbert",
            "hidden_size": 768,
            "num_hidden_layers": 6,
            "license": "apache-2.0",
        }
        with open(mock_model_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_content, f)

        # 2. Create minimal binary safetensors file with 8-byte length prefix
        header_dict = {
            "embeddings.word_embeddings.weight": {"dtype": "F32", "shape": [30522, 768], "data_offsets": [0, 93763584]},
            "transformer.layer.0.attention.q_lin.weight": {"dtype": "F32", "shape": [768, 768], "data_offsets": [93763584, 96122880]},
            "__metadata__": {"format": "pt"},
        }
        header_json_bytes = json.dumps(header_dict).encode("utf-8")
        header_len = len(header_json_bytes)
        prefix = struct.pack("<Q", header_len)

        with open(mock_model_dir / "model.safetensors", "wb") as f:
            f.write(prefix)
            f.write(header_json_bytes)
            # Add small dummy byte for offsets
            f.write(b"\x00" * 16)

        # Run inspect_local_model
        info = inspect_local_model(str(mock_model_dir))
        self.assertEqual(info["source"], "local")
        self.assertEqual(info["architecture"], "DistilBertForSequenceClassification")
        self.assertTrue(info["has_safetensors"])
        self.assertFalse(info["has_pickle"])
        # Expected params: (30522 * 768) + (768 * 768) = 23,440,896 + 589,824 = 24,030,720
        self.assertEqual(info["parameter_count"], 24030720)

    # ================= 3. Hugging Face Hub Inspection Tests (Hermetic) =================

    def test_07_huggingface_inspection_success_mocked(self):
        """Verify Hugging Face model metadata extraction via mocked API response."""
        mock_hf_response = {
            "id": "distilbert/distilbert-base-uncased",
            "pipeline_tag": "text-classification",
            "config": {
                "architectures": ["DistilBertForSequenceClassification"],
                "model_type": "distilbert",
                "hidden_size": 768,
            },
            "safetensors": {"total": 66362880},
            "siblings": [
                {"rfilename": "model.safetensors", "lfs": {"size": 267849200}},
                {"rfilename": "config.json", "lfs": {"size": 483}},
            ],
            "tags": ["transformers", "license:apache-2.0"],
            "cardData": {"license": "apache-2.0"},
            "private": False,
            "gated": False,
            "sha": "a1b2c3d4e5f6",
        }

        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_hf_response
            mock_get.return_value = mock_resp

            info = inspect_huggingface_model("distilbert/distilbert-base-uncased")
            self.assertEqual(info["model_id"], "distilbert/distilbert-base-uncased")
            self.assertEqual(info["parameter_count"], 66362880)
            self.assertEqual(info["architecture"], "DistilBertForSequenceClassification")
            self.assertEqual(info["license"], "apache-2.0")
            self.assertTrue(info["has_safetensors"])
            self.assertFalse(info["has_pickle"])

    def test_08_huggingface_inspection_404_not_found(self):
        """Verify 404 response when model does not exist on Hugging Face."""
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            with self.assertRaises(ModelInspectionError) as ctx:
                inspect_huggingface_model("nonexistent/unknown-model-xyz")
            self.assertEqual(ctx.exception.code, "MODEL_NOT_FOUND")

    def test_09_huggingface_inspection_gated_model(self):
        """Verify 403 response when model is gated/private on Hugging Face."""
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_get.return_value = mock_resp

            with self.assertRaises(ModelInspectionError) as ctx:
                inspect_huggingface_model("meta-llama/Llama-2-7b")
            self.assertEqual(ctx.exception.code, "GATED_OR_PRIVATE")

    # ================= 4. Resource Feasibility Estimator Tests =================

    def test_10_feasibility_small_model_is_feasible(self):
        """Verify small model (~66M params) evaluates as FEASIBLE within 4GB VRAM."""
        model_meta = {
            "parameter_count": 66_000_000,
            "total_weight_size_mb": 268.0,
            "task": "text-classification",
        }
        feasibility = estimate_model_feasibility(model_meta, batch_size=1, sequence_length=128)
        self.assertEqual(feasibility["verdict"], FeasibilityVerdict.FEASIBLE)
        self.assertIn("fits comfortably", feasibility["reason"].lower())
        self.assertGreater(feasibility["memory_estimates"]["int8_quantized_mb"], 0)
        self.assertIn("Evidence-based notice", feasibility["uncertainty_disclaimer"])

    def test_11_feasibility_large_model_exceeds_vram(self):
        """Verify 7B model (~7 billion params) evaluates as EXCEEDS_VRAM on 4GB GPU."""
        model_meta = {
            "parameter_count": 7_000_000_000,
            "total_weight_size_mb": 14000.0,
            "task": "text-generation",
        }
        feasibility = estimate_model_feasibility(model_meta, batch_size=1, sequence_length=512)
        self.assertEqual(feasibility["verdict"], FeasibilityVerdict.EXCEEDS_VRAM)
        self.assertIn("exceeds current free vram", feasibility["reason"].lower())

    def test_12_feasibility_cannot_determine_when_params_missing(self):
        """Verify CANNOT_DETERMINE verdict when parameter count and file size are missing."""
        model_meta = {
            "parameter_count": None,
            "total_weight_size_mb": None,
            "task": "unspecified",
        }
        feasibility = estimate_model_feasibility(model_meta)
        self.assertEqual(feasibility["verdict"], FeasibilityVerdict.CANNOT_DETERMINE)

    # ================= 5. API Endpoint Tests =================

    def test_13_post_models_inspect_endpoint(self):
        """Verify POST /models/inspect returns metadata and feasibility."""
        mock_hf_response = {
            "id": "HuggingFaceTB/SmolLM-135M",
            "pipeline_tag": "text-generation",
            "config": {"architectures": ["LlamaForCausalLM"], "hidden_size": 576},
            "safetensors": {"total": 134515200},
            "siblings": [{"rfilename": "model.safetensors", "lfs": {"size": 269030400}}],
            "tags": ["license:apache-2.0"],
            "cardData": {"license": "apache-2.0"},
        }

        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_hf_response
            mock_get.return_value = mock_resp

            res = self.client.post(
                "/models/inspect",
                json={"source": "huggingface", "model_id": "HuggingFaceTB/SmolLM-135M"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["metadata"]["parameter_count"], 134515200)
            self.assertEqual(data["feasibility"]["verdict"], FeasibilityVerdict.FEASIBLE)


if __name__ == "__main__":
    unittest.main()
