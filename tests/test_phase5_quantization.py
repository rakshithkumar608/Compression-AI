"""
Hermetic Unit & Integration Tests for EcoCompress AI Phase 5: Model Quantization.
Validates preflight checks, disk headroom, non-destructive safety, C: drive rejection,
dynamic INT8 quantization, Safetensors serialization, cancellation, and error cleanup.
Uses synthetic models to test the pipeline thoroughly without modifying production weights.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import torch
import safetensors.torch

# Ensure services/api is in sys.path
import sys
API_DIR = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(API_DIR))

from services.quantization_service import (
    QuantizationConfig,
    QuantizationPipeline,
    QuantizationPreflightError,
    QuantizationCancelledError,
    QuantizationExecutionError,
)


class TestPhase5ModelQuantization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Anchor temporary test directory strictly on D: drive or tempfile
        cls.test_root = Path(tempfile.mkdtemp(prefix="ecocompress_test_p5_"))
        cls.synthetic_model_dir = cls.test_root / "synthetic_model"
        cls.synthetic_model_dir.mkdir(parents=True, exist_ok=True)

        # Create a small synthetic safetensors model for testing
        # 2 Linear layers (2D) + 1 embedding layer (2D with 'embed' in name) + 1 norm (1D)
        tensors = {
            "model.embed_tokens.weight": torch.randn(100, 32, dtype=torch.float32),
            "model.layers.0.self_attn.q_proj.weight": torch.randn(32, 32, dtype=torch.float32),
            "model.layers.0.mlp.gate_proj.weight": torch.randn(64, 32, dtype=torch.float32),
            "model.norm.weight": torch.ones(32, dtype=torch.float32),
        }
        safetensors.torch.save_file(tensors, str(cls.synthetic_model_dir / "model.safetensors"))

        # Create config.json
        config_data = {
            "architectures": ["SyntheticLlamaModel"],
            "hidden_size": 32,
            "vocab_size": 100,
        }
        with open(cls.synthetic_model_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        # Create dummy tokenizer.json
        with open(cls.synthetic_model_dir / "tokenizer.json", "w", encoding="utf-8") as f:
            f.write('{"model": "dummy"}')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_root, ignore_errors=True)

    def setUp(self):
        self.pipeline = QuantizationPipeline()

    # -------------------------------------------------------------
    # 1. Preflight Validation Tests
    # -------------------------------------------------------------
    def test_01_preflight_rejects_unsupported_quantization_method(self):
        """Verify preflight rejects unapproved quantization methods."""
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=self.test_root / "out_unsupported",
            quantization_method="unsupported-quant-4bit",
        )
        with self.assertRaises(QuantizationPreflightError) as ctx:
            self.pipeline.validate_preflight(cfg)
        self.assertIn("Unsupported quantization method", str(ctx.exception))

    def test_02_preflight_rejects_nonexistent_source_path(self):
        """Verify preflight rejects nonexistent model paths."""
        cfg = QuantizationConfig(
            source_model_path=self.test_root / "nonexistent_model",
            output_dir=self.test_root / "out_missing",
            quantization_method="torch-dynamic-int8",
        )
        with self.assertRaises(QuantizationPreflightError) as ctx:
            self.pipeline.validate_preflight(cfg)
        self.assertIn("does not exist on disk", str(ctx.exception))

    def test_03_preflight_rejects_missing_safetensors_file(self):
        """Verify preflight rejects directories without model.safetensors."""
        empty_dir = self.test_root / "empty_model_dir"
        empty_dir.mkdir(parents=True, exist_ok=True)
        # only config.json, no weights
        with open(empty_dir / "config.json", "w") as f:
            f.write("{}")

        cfg = QuantizationConfig(
            source_model_path=empty_dir,
            output_dir=self.test_root / "out_no_weights",
            quantization_method="torch-dynamic-int8",
        )
        with self.assertRaises(QuantizationPreflightError) as ctx:
            self.pipeline.validate_preflight(cfg)
        self.assertIn("missing 'model.safetensors'", str(ctx.exception))

    def test_04_preflight_rejects_destination_on_c_drive(self):
        """Verify preflight rejects output targeting C: drive (Storage Protection Rule)."""
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir="C:/dangerous_output_dir",
            quantization_method="torch-dynamic-int8",
        )
        with self.assertRaises(QuantizationPreflightError) as ctx:
            self.pipeline.validate_preflight(cfg)
        self.assertIn("targets C: drive", str(ctx.exception))

    def test_05_preflight_rejects_identical_source_and_destination(self):
        """Verify non-destructive safety: output directory cannot be the same as source."""
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=self.synthetic_model_dir,
            quantization_method="torch-dynamic-int8",
        )
        with self.assertRaises(QuantizationPreflightError) as ctx:
            self.pipeline.validate_preflight(cfg)
        self.assertIn("cannot be identical to source", str(ctx.exception))

    def test_06_preflight_insufficient_disk_space_mock(self):
        """Verify preflight halts if free disk space is below required threshold."""
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=self.test_root / "out_disk_test",
            min_disk_headroom_gb=10.0,
        )
        # Mock psutil.disk_usage to report only 0.5 GB free
        mock_usage = MagicMock()
        mock_usage.free = 500 * 1024 * 1024  # 500 MB
        with patch("psutil.disk_usage", return_value=mock_usage):
            with self.assertRaises(QuantizationPreflightError) as ctx:
                self.pipeline.validate_preflight(cfg)
            self.assertIn("Insufficient disk space", str(ctx.exception))

    # -------------------------------------------------------------
    # 2. Quantization Execution & Output Verification Tests
    # -------------------------------------------------------------
    def test_07_quantize_synthetic_model_success(self):
        """Verify end-to-end dynamic INT8 quantization of synthetic model."""
        out_dir = self.test_root / "candidate_int8"
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=out_dir,
            quantization_method="torch-dynamic-int8",
            min_disk_headroom_gb=0.01,
        )

        progress_events = []
        def on_progress(step: str, pct: int):
            progress_events.append((step, pct))

        res = self.pipeline.quantize_model(config=cfg, progress_callback=on_progress)

        # 1. Verify result structure
        self.assertEqual(res.quantization_method, "torch-dynamic-int8")
        self.assertEqual(res.quantized_layers_count, 2)  # q_proj and gate_proj
        self.assertGreater(res.original_size_mb, 0.0)
        self.assertGreater(res.quantized_size_mb, 0.0)
        self.assertEqual(res.output_directory, str(out_dir))

        # 2. Verify output files
        self.assertTrue((out_dir / "model.safetensors").exists())
        self.assertTrue((out_dir / "config.json").exists())
        self.assertTrue((out_dir / "quantization_manifest.json").exists())

        # 3. Verify quantized weights inside model.safetensors
        loaded_tensors = safetensors.torch.load_file(str(out_dir / "model.safetensors"))

        # Linear weights must be int8
        self.assertEqual(loaded_tensors["model.layers.0.self_attn.q_proj.weight"].dtype, torch.int8)
        self.assertEqual(loaded_tensors["model.layers.0.mlp.gate_proj.weight"].dtype, torch.int8)
        self.assertIn("model.layers.0.self_attn.q_proj.weight_scale", loaded_tensors)
        self.assertIn("model.layers.0.self_attn.q_proj.weight_zero_point", loaded_tensors)

        # Embedding must remain float32
        self.assertEqual(loaded_tensors["model.embed_tokens.weight"].dtype, torch.float32)
        # Norm must remain float32
        self.assertEqual(loaded_tensors["model.norm.weight"].dtype, torch.float32)

        # 4. Verify config.json has quantization_config
        with open(out_dir / "config.json", "r") as f:
            saved_cfg = json.load(f)
        self.assertIn("quantization_config", saved_cfg)
        self.assertEqual(saved_cfg["quantization_config"]["bits"], 8)

        # 5. Verify progress callbacks reached 100%
        self.assertEqual(progress_events[-1][1], 100)

    # -------------------------------------------------------------
    # 3. Cooperative Cancellation Test
    # -------------------------------------------------------------
    def test_08_quantization_cancellation(self):
        """Verify cancellation stops execution cleanly and cleans up temporary files."""
        out_dir = self.test_root / "candidate_cancelled"
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=out_dir,
            min_disk_headroom_gb=0.01,
        )

        def cancel_immediately():
            return True

        with self.assertRaises(QuantizationCancelledError):
            self.pipeline.quantize_model(
                config=cfg,
                cancellation_check=cancel_immediately,
            )

        # Target output directory must NOT exist (atomic rollback)
        self.assertFalse(out_dir.exists())

    # -------------------------------------------------------------
    # 4. Rollback and Cleanup on Serialization Failure
    # -------------------------------------------------------------
    def test_09_quantization_failure_cleans_up_staging_directory(self):
        """Verify that an unexpected failure cleans up temporary staging files."""
        out_dir = self.test_root / "candidate_failed"
        cfg = QuantizationConfig(
            source_model_path=self.synthetic_model_dir,
            output_dir=out_dir,
            min_disk_headroom_gb=0.01,
        )

        with patch("safetensors.torch.save_file", side_effect=IOError("Simulated disk error during save")):
            with self.assertRaises(QuantizationExecutionError) as ctx:
                self.pipeline.quantize_model(config=cfg)
            self.assertIn("Simulated disk error", str(ctx.exception))

        # Target directory must NOT exist
        self.assertFalse(out_dir.exists())
        # No staging directory tmp_quant_* left over in parent
        tmp_dirs = list(self.test_root.glob("tmp_quant_*"))
        self.assertEqual(len(tmp_dirs), 0)


if __name__ == "__main__":
    unittest.main()
