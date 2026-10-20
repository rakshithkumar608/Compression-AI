"""
Hermetic Unit & Integration Tests for EcoCompress AI Phase 7: Export Packaging, Verification & Delivery.
Validates SHA-256 manifest generation, storage safety guards, archive creation,
checksum verification, tamper detection, and candidate package integrity.
"""

import hashlib
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

# Ensure services/api is in sys.path
API_DIR = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(API_DIR))

import safetensors.torch
import torch

from database import init_db, get_db
from services.export_service import (
    ExportService,
    ExportPreflightError,
    ExportVerificationError,
    compute_file_sha256,
)


class TestPhase7ExportPackaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Anchor temporary test root strictly on D: drive
        cls.test_root = Path("D:/Projects/Compression AI/exports/tmp_test_p7").resolve()
        cls.test_root.mkdir(parents=True, exist_ok=True)

        cls.db_path = cls.test_root / "test_export.db"
        init_db(cls.db_path)

        # Seed mock experiment and benchmark records
        cls.exp_id = "exp-test-phase7-001"
        with get_db(cls.db_path) as conn:
            conn.execute(
                """
                INSERT INTO experiments (
                    id, name, model_id, task, optimization_method, workload_config,
                    thresholds, status, created_at, updated_at, acceptance_decision
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.exp_id,
                    "Phase 7 Test Exp",
                    "HuggingFaceTB/SmolLM2-360M-Instruct",
                    "text-generation",
                    "torch-dynamic-int8",
                    json.dumps({"task": "text-generation", "sample_count": 10}),
                    json.dumps({"max_accuracy_drop_pct": 5.0, "min_latency_speedup_pct": 10.0}),
                    "completed",
                    "2026-10-20 10:00:00 UTC",
                    "2026-10-20 10:30:00 UTC",
                    json.dumps({"passed": True, "reasons": ["Test passed"]}),
                ),
            )
            conn.execute(
                """
                INSERT INTO benchmark_results (
                    experiment_id, candidate_type, model_revision,
                    median_latency_ms, p95_latency_ms, peak_memory_mb, artifact_size_mb,
                    hardware_device, runtime_name, warmup_runs, measured_runs, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.exp_id,
                    "baseline",
                    "a10cc1512eabd3dde888204e902eca88bddb4951",
                    190.37,
                    3417.07,
                    1850.34,
                    690.15,
                    "CPU",
                    "PyTorch 2.12.0+cpu",
                    3,
                    10,
                    "2026-10-20 10:15:00 UTC",
                ),
            )
            conn.execute(
                """
                INSERT INTO benchmark_results (
                    experiment_id, candidate_type, model_revision,
                    median_latency_ms, p95_latency_ms, peak_memory_mb, artifact_size_mb,
                    hardware_device, runtime_name, warmup_runs, measured_runs, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cls.exp_id,
                    "candidate",
                    "a10cc1512eabd3dde888204e902eca88bddb4951",
                    3128.74,
                    3681.01,
                    1958.42,
                    390.20,
                    "CPU",
                    "PyTorch 2.12.0+cpu",
                    3,
                    10,
                    "2026-10-20 10:45:00 UTC",
                ),
            )
            conn.commit()

        # Create mock candidate directory
        cls.cand_dir = cls.test_root / "mock_candidate_dir"
        cls.cand_dir.mkdir(parents=True, exist_ok=True)

        w_int8 = torch.randint(-128, 127, (16, 16), dtype=torch.int8)
        scale = torch.tensor([0.05], dtype=torch.float32)
        zp = torch.tensor([0], dtype=torch.int8)
        tensors = {
            "model.embed_tokens.weight": torch.randn(20, 16, dtype=torch.float32),
            "model.layers.0.self_attn.q_proj.weight": w_int8,
            "model.layers.0.self_attn.q_proj.weight_scale": scale,
            "model.layers.0.self_attn.q_proj.weight_zero_point": zp,
            "model.norm.weight": torch.ones(16, dtype=torch.float32),
        }
        safetensors.torch.save_file(tensors, str(cls.cand_dir / "model.safetensors"))
        with open(cls.cand_dir / "config.json", "w") as f:
            json.dump({"architectures": ["LlamaForCausalLM"]}, f)
        with open(cls.cand_dir / "tokenizer.json", "w") as f:
            f.write('{"test_tokenizer": true}')

        cls.exports_dir = cls.test_root / "out_exports"
        cls.export_service = ExportService(exports_dir=cls.exports_dir, db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        # Cleanup temporary test files
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root, ignore_errors=True)

    def test_01_compute_file_sha256(self):
        """Verifies buffered SHA-256 calculation matches standard hashlib."""
        sample_file = self.cand_dir / "config.json"
        computed_sha = compute_file_sha256(sample_file)
        expected_sha = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        self.assertEqual(computed_sha, expected_sha)
        self.assertEqual(len(computed_sha), 64)

    def test_02_preflight_rejection_c_drive(self):
        """Verifies storage guard blocks exports configured to write to C: drive."""
        c_service = ExportService(exports_dir="C:/dangerous_export_path", db_path=self.db_path)
        with self.assertRaises(ExportPreflightError) as ctx:
            c_service.validate_preflight(self.exp_id, self.cand_dir)
        self.assertIn("C: drive", str(ctx.exception))

    def test_03_preflight_missing_experiment(self):
        """Verifies preflight rejects unknown experiment ID."""
        with self.assertRaises(ExportPreflightError) as ctx:
            self.export_service.validate_preflight("nonexistent-exp-id", self.cand_dir)
        self.assertIn("not found in database", str(ctx.exception))

    def test_04_preflight_missing_candidate_files(self):
        """Verifies preflight rejects candidate directory lacking model weights or config."""
        empty_dir = self.test_root / "empty_candidate_dir"
        empty_dir.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(ExportPreflightError) as ctx:
            self.export_service.validate_preflight(self.exp_id, empty_dir)
        self.assertIn("missing 'model.safetensors'", str(ctx.exception))

    def test_05_package_creation(self):
        """Verifies export packaging generates manifest, loader, model card, and zip archive."""
        res = self.export_service.create_export_package(
            exp_id=self.exp_id,
            candidate_dir=self.cand_dir,
            create_zip=True,
        )
        self.assertEqual(res["export_id"], f"export_{self.exp_id}_int8")
        self.assertTrue(Path(res["package_directory"]).exists())
        self.assertTrue(Path(res["archive_path"]).exists())
        self.assertGreater(res["archive_size_mb"], 0)
        self.assertIsNotNone(res["archive_sha256"])

        # Check required files in package
        pkg_path = Path(res["package_directory"])
        self.assertTrue((pkg_path / "manifest.json").exists())
        self.assertTrue((pkg_path / "loader.py").exists())
        self.assertTrue((pkg_path / "MODEL_CARD.md").exists())
        self.assertTrue((pkg_path / "model.safetensors").exists())
        self.assertTrue((pkg_path / "config.json").exists())
        self.assertTrue((pkg_path / "requirements.txt").exists())

    def test_06_manifest_integrity_and_truthfulness(self):
        """Verifies manifest data structure, provenance, and absence of fabricated metrics."""
        manifest_file = self.exports_dir / f"export_{self.exp_id}_int8" / "manifest.json"
        self.assertTrue(manifest_file.exists())

        with open(manifest_file, "r") as f:
            data = json.load(f)

        self.assertEqual(data["format_version"], "ecocompress-export-manifest-v1")
        self.assertEqual(data["model_metadata"]["architecture"], "LlamaForCausalLM")
        self.assertEqual(data["model_metadata"]["license"], "Apache-2.0")

        # Runtime compatibility: explicitly states HF direct loading is NOT supported
        self.assertFalse(data["runtime_compatibility"]["direct_huggingface_loadable"])
        self.assertTrue(data["runtime_compatibility"]["custom_loader_required"])

        # Environmental metrics: explicitly null / unavailable (no fabricated metrics)
        env = data["environmental_metrics"]
        self.assertIsNone(env["energy_joules"])
        self.assertIsNone(env["carbon_grams"])
        self.assertIsNone(env["water_milliliters"])
        self.assertEqual(env["status"], "unavailable")

        # Files array contains valid hashes
        files = data["files"]
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            self.assertEqual(len(f["sha256"]), 64)
            self.assertGreater(f["size_bytes"], 0)

    def test_07_verify_package_directory_success(self):
        """Verifies verify_package succeeds on the created export directory."""
        pkg_dir = self.exports_dir / f"export_{self.exp_id}_int8"
        res = self.export_service.verify_package(pkg_dir)
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["missing_files"]), 0)
        self.assertEqual(len(res["mismatched_files"]), 0)
        self.assertGreaterEqual(res["verified_files_count"], 4)

    def test_08_verify_package_zip_success(self):
        """Verifies verify_package succeeds on the created zip archive."""
        zip_file = self.exports_dir / f"export_{self.exp_id}_int8.zip"
        res = self.export_service.verify_package(zip_file)
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["missing_files"]), 0)
        self.assertEqual(len(res["mismatched_files"]), 0)

    def test_09_verify_detects_tampered_file(self):
        """Verifies verify_package detects if a file has been altered."""
        tamper_dir = self.test_root / "tamper_test_pkg"
        shutil.copytree(self.exports_dir / f"export_{self.exp_id}_int8", tamper_dir)

        # Alter config.json
        with open(tamper_dir / "config.json", "w") as f:
            f.write('{"tampered": true}')

        res = self.export_service.verify_package(tamper_dir)
        self.assertFalse(res["passed"])
        self.assertIn("config.json", [m["file"] for m in res["mismatched_files"]])

    def test_10_verify_detects_missing_file(self):
        """Verifies verify_package detects if a required file is missing."""
        missing_dir = self.test_root / "missing_file_test_pkg"
        shutil.copytree(self.exports_dir / f"export_{self.exp_id}_int8", missing_dir)

        # Delete loader.py
        (missing_dir / "loader.py").unlink()

        res = self.export_service.verify_package(missing_dir)
        self.assertFalse(res["passed"])
        self.assertIn("loader.py", res["missing_files"])

    def test_11_verify_real_accepted_candidate_package(self):
        """Integration test: verifies the actual real Phase 7 candidate export on D:."""
        real_pkg_dir = Path("D:/Projects/Compression AI/exports/export_exp-20261020102101-4f000a_int8")
        real_zip_file = Path("D:/Projects/Compression AI/exports/export_exp-20261020102101-4f000a_int8.zip")

        if real_pkg_dir.exists():
            real_service = ExportService()
            dir_res = real_service.verify_package(real_pkg_dir)
            self.assertTrue(dir_res["passed"])
            self.assertEqual(dir_res["verified_files_count"], 10)
            self.assertEqual(len(dir_res["missing_files"]), 0)
            self.assertEqual(len(dir_res["mismatched_files"]), 0)

        if real_zip_file.exists():
            real_service = ExportService()
            zip_res = real_service.verify_package(real_zip_file)
            self.assertTrue(zip_res["passed"])
            self.assertEqual(zip_res["verified_files_count"], 10)
            self.assertEqual(len(zip_res["missing_files"]), 0)
            self.assertEqual(len(zip_res["mismatched_files"]), 0)

    def test_12_exported_loader_compiles(self):
        """Verifies that generated loader.py compiles cleanly without Python syntax errors."""
        loader_path = self.exports_dir / f"export_{self.exp_id}_int8" / "loader.py"
        self.assertTrue(loader_path.exists())
        code = loader_path.read_text(encoding="utf-8")
        compiled = compile(code, str(loader_path), "exec")
        self.assertIsNotNone(compiled)

    def test_13_security_rejects_path_traversal_forward_slash(self):
        """Priority 0 Security: Rejects ZIP archives containing '../' relative traversal."""
        import zipfile
        bad_zip = self.test_root / "evil_traversal_forward.zip"
        outside_marker = self.test_root / "evil_marker_forward.txt"
        if outside_marker.exists():
            outside_marker.unlink()

        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("../evil_marker_forward.txt", "MALICIOUS CONTENT")
            zf.writestr("manifest.json", "{}")

        with self.assertRaises(ExportVerificationError) as ctx:
            self.export_service.verify_package(bad_zip)
        self.assertIn("Path traversal", str(ctx.exception))
        self.assertFalse(outside_marker.exists())

    def test_14_security_rejects_path_traversal_backslash(self):
        """Priority 0 Security: Rejects ZIP archives containing '..\\' Windows backslash traversal."""
        import zipfile
        bad_zip = self.test_root / "evil_traversal_back.zip"
        outside_marker = self.test_root / "evil_marker_back.txt"
        if outside_marker.exists():
            outside_marker.unlink()

        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("..\\evil_marker_back.txt", "MALICIOUS CONTENT")
            zf.writestr("manifest.json", "{}")

        with self.assertRaises(ExportVerificationError) as ctx:
            self.export_service.verify_package(bad_zip)
        self.assertIn("Path traversal", str(ctx.exception))
        self.assertFalse(outside_marker.exists())

    def test_15_security_rejects_absolute_path_posix(self):
        """Priority 0 Security: Rejects ZIP archives containing POSIX absolute paths."""
        import zipfile
        bad_zip = self.test_root / "evil_absolute_posix.zip"
        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("/etc/passwd_evil.txt", "MALICIOUS CONTENT")
            zf.writestr("manifest.json", "{}")

        with self.assertRaises(ExportVerificationError) as ctx:
            self.export_service.verify_package(bad_zip)
        self.assertIn("Absolute path", str(ctx.exception))

    def test_16_security_rejects_windows_drive_path(self):
        """Priority 0 Security: Rejects ZIP archives containing Windows drive-qualified paths."""
        import zipfile
        bad_zip = self.test_root / "evil_drive_path.zip"
        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("C:\\Windows\\System32\\evil.dll", "MALICIOUS CONTENT")
            zf.writestr("manifest.json", "{}")

        with self.assertRaises(ExportVerificationError) as ctx:
            self.export_service.verify_package(bad_zip)
        self.assertIn("Windows drive-qualified path", str(ctx.exception))

    def test_17_security_rejects_unc_path(self):
        """Priority 0 Security: Rejects ZIP archives containing UNC network paths."""
        import zipfile
        bad_zip = self.test_root / "evil_unc_path.zip"
        with zipfile.ZipFile(str(bad_zip), "w") as zf:
            zf.writestr("\\\\attacker.com\\share\\evil.txt", "MALICIOUS CONTENT")
            zf.writestr("manifest.json", "{}")

        with self.assertRaises(ExportVerificationError) as ctx:
            self.export_service.verify_package(bad_zip)
        self.assertIn("UNC path", str(ctx.exception))

    def test_18_security_allows_valid_nested_directories(self):
        """Priority 0 Security: Allows legitimate nested relative subdirectories."""
        import zipfile
        nested_zip = self.test_root / "valid_nested.zip"
        extract_dest = self.test_root / "valid_nested_extracted"
        extract_dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(nested_zip), "w") as zf:
            zf.writestr("models/subfolder/config.json", '{"nested": true}')
            zf.writestr("metadata/provenance.json", '{"provenance": true}')

        with zipfile.ZipFile(str(nested_zip), "r") as zf:
            self.export_service.safe_extract_zip(zf, extract_dest)

        self.assertTrue((extract_dest / "models" / "subfolder" / "config.json").exists())
        self.assertTrue((extract_dest / "metadata" / "provenance.json").exists())

    def test_19_security_atomic_rejection_no_partial_writes(self):
        """Priority 0 Security: Pre-extraction validation blocks partial writes on mixed archives."""
        import zipfile
        mixed_zip = self.test_root / "mixed_malicious.zip"
        extract_dest = self.test_root / "atomic_extract_dest"
        extract_dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(mixed_zip), "w") as zf:
            zf.writestr("valid_file_1.txt", "VALID FILE 1")
            zf.writestr("..\\evil_escape.txt", "EVIL ESCAPE")
            zf.writestr("valid_file_2.txt", "VALID FILE 2")

        with zipfile.ZipFile(str(mixed_zip), "r") as zf:
            with self.assertRaises(ExportVerificationError):
                self.export_service.safe_extract_zip(zf, extract_dest)

        # Confirm ZERO files were written before rejection
        extracted_files = list(extract_dest.glob("*"))
        self.assertEqual(len(extracted_files), 0, "Partial write detected! Security invariant violated.")

    def test_20_loader_has_local_files_only(self):
        """Priority 1 Portability: Loader specifies local_files_only=True and has requirements.txt."""
        loader_path = self.exports_dir / f"export_{self.exp_id}_int8" / "loader.py"
        self.assertTrue(loader_path.exists())
        code = loader_path.read_text(encoding="utf-8")
        self.assertIn("local_files_only=True", code)

        req_path = self.exports_dir / f"export_{self.exp_id}_int8" / "requirements.txt"
        self.assertTrue(req_path.exists())
        req_content = req_path.read_text(encoding="utf-8")
        self.assertIn("torch", req_content)
        self.assertIn("transformers", req_content)
        self.assertIn("safetensors", req_content)



if __name__ == "__main__":
    unittest.main()
