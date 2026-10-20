"""
Unit tests for EcoCompress AI Phase 1 API endpoints.
Tests /health and /system response contracts using Python unittest.
"""

import sys
import os
import unittest

# Add services/api to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "api")))

from fastapi.testclient import TestClient
from main import app


class TestApiHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("Phase 1", data["phase"])
        self.assertEqual(data["service"], "EcoCompress AI Core API")

    def test_system_diagnostics_endpoint(self):
        response = self.client.get("/system")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("os", data)
        self.assertGreater(data["total_ram_gb"], 0)
        self.assertIn("storage", data)
        self.assertIn("gpu_profile", data)
        self.assertEqual(data["gpu_profile"]["vram_mb"], 4096)
        self.assertEqual(data["gpu_profile"]["model"], "NVIDIA GeForce RTX 2050 Laptop GPU")


if __name__ == "__main__":
    unittest.main()
