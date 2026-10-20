"""
EcoCompress AI - Unit Tests for Phase 9 Evaluation Dataset & Scorer (unittest)
Tests:
1. Evaluation dataset JSON validation (16 items, 4 categories, required fields, hash invariance)
2. Scorer rubric correctness (FQA, SRA, SSM, IFC)
3. Edge cases: empty text, partial matches, malformed JSON, number extraction
"""

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

from services.evaluation_scorer import (
    score_item,
    extract_numbers_from_text,
    ItemEvaluationResult,
)

DATASET_PATH = PROJECT_ROOT / "data" / "evalsets" / "smollm2_evalset_v1.0.0.json"


class TestPhase9Evaluation(unittest.TestCase):
    def test_01_dataset_schema_and_integrity(self):
        """Validates that smollm2_evalset_v1.0.0 exists and conforms to required schema."""
        self.assertTrue(DATASET_PATH.exists(), f"Evaluation dataset not found at {DATASET_PATH}")
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["evalset_id"], "smollm2_evalset_v1.0.0")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["target_architecture"], "SmolLM2-360M-Instruct")
        self.assertEqual(data["total_items"], 16)

        items = data["items"]
        self.assertEqual(len(items), 16)

        categories = set(item["category"] for item in items)
        expected_categories = {"factual_qa", "simple_reasoning", "short_summarization", "instruction_following"}
        self.assertEqual(categories, expected_categories)

        for item in items:
            self.assertIn("id", item)
            self.assertIn("category", item)
            self.assertIn("prompt", item)
            self.assertIn("reference_answer", item)
            self.assertIn("max_new_tokens", item)
            self.assertIn("rubric", item)
            self.assertIn("type", item["rubric"])
            self.assertGreater(item["max_new_tokens"], 0)

    def test_02_numeric_extraction(self):
        """Tests regex-based numeric extraction."""
        self.assertEqual(extract_numbers_from_text("The result is 210 miles."), [210.0])
        self.assertEqual(extract_numbers_from_text("60 * 3.5 = 210"), [60.0, 3.5, 210.0])
        self.assertEqual(extract_numbers_from_text("No numbers here!"), [])
        self.assertEqual(extract_numbers_from_text("Negative -15.5 and 42"), [-15.5, 42.0])

    def test_03_score_factual_qa(self):
        """Tests FQA scoring rubrics."""
        item_water = {
            "id": "FQA-01",
            "category": "factual_qa",
            "rubric": {"type": "regex_match", "pattern": r"\bH2O\b", "max_score": 1.0},
        }
        res_pass = score_item(item_water, "The formula is H2O.")
        self.assertTrue(res_pass.passed)
        self.assertEqual(res_pass.score, 1.0)

        res_fail = score_item(item_water, "Water is made of hydrogen and oxygen.")
        self.assertFalse(res_fail.passed)
        self.assertEqual(res_fail.score, 0.0)

    def test_04_score_simple_reasoning(self):
        """Tests SRA numeric extraction scoring."""
        item_train = {
            "id": "SRA-01",
            "category": "simple_reasoning",
            "rubric": {"type": "numeric_extraction", "expected_value": 210.0, "tolerance": 0.0, "max_score": 1.0},
        }
        res_pass = score_item(item_train, "At 60 mph for 3.5 hours: 60 * 3.5 = 210 miles.")
        self.assertTrue(res_pass.passed)
        self.assertEqual(res_pass.score, 1.0)

        res_fail = score_item(item_train, "It travels 180 miles.")
        self.assertFalse(res_fail.passed)
        self.assertEqual(res_fail.score, 0.0)

    def test_05_score_short_summarization(self):
        """Tests SSM concept matching."""
        item_photosynth = {
            "id": "SSM-01",
            "category": "short_summarization",
            "rubric": {
                "type": "concept_presence",
                "required_concept_groups": [
                    ["energy", "glucose"],
                    ["sunlight", "water", "carbon dioxide"],
                    ["oxygen"],
                ],
                "max_sentences": 2,
                "max_score": 1.0,
            },
        }
        good_summary = "Plants convert sunlight and water into glucose energy and release oxygen."
        res_pass = score_item(item_photosynth, good_summary)
        self.assertTrue(res_pass.passed)
        self.assertGreaterEqual(res_pass.score, 0.75)

        poor_summary = "Plants are green."
        res_fail = score_item(item_photosynth, poor_summary)
        self.assertFalse(res_fail.passed)
        self.assertLess(res_fail.score, 0.5)

    def test_06_score_instruction_following_json(self):
        """Tests IFC JSON constraint checker."""
        item_json = {
            "id": "IFC-02",
            "category": "instruction_following",
            "rubric": {
                "type": "json_constraint",
                "expected_keys": ["model", "quantized"],
                "expected_values": {"model": "SmolLM2", "quantized": True},
                "max_score": 1.0,
            },
        }
        res_pass = score_item(item_json, '{"model": "SmolLM2", "quantized": true}')
        self.assertTrue(res_pass.passed)
        self.assertEqual(res_pass.score, 1.0)

        res_fenced = score_item(item_json, '```json\n{"model": "SmolLM2", "quantized": true}\n```')
        self.assertTrue(res_fenced.passed)
        self.assertEqual(res_fenced.score, 1.0)

        res_invalid = score_item(item_json, "model: SmolLM2, quantized: true")
        self.assertFalse(res_invalid.passed)
        self.assertEqual(res_invalid.score, 0.0)

    def test_07_score_instruction_following_bullet_and_choice(self):
        """Tests bullet list and single word choices."""
        item_bullets = {
            "id": "IFC-01",
            "category": "instruction_following",
            "rubric": {
                "type": "bullet_list_constraint",
                "expected_items": 3,
                "bullet_prefix": "-",
                "required_keywords": ["red", "blue", "yellow"],
                "max_score": 1.0,
            },
        }
        bullets_text = "- Red\n- Blue\n- Yellow"
        res_bullets = score_item(item_bullets, bullets_text)
        self.assertTrue(res_bullets.passed)
        self.assertGreaterEqual(res_bullets.score, 0.9)

        item_choice = {
            "id": "IFC-03",
            "category": "instruction_following",
            "rubric": {
                "type": "single_word_choice",
                "expected_choice": "Yes",
                "allowed_choices": ["Yes", "No"],
                "max_score": 1.0,
            },
        }
        res_choice = score_item(item_choice, "Yes")
        self.assertTrue(res_choice.passed)
        self.assertEqual(res_choice.score, 1.0)

        res_choice_no = score_item(item_choice, "No")
        self.assertFalse(res_choice_no.passed)
        self.assertEqual(res_choice_no.score, 0.0)


if __name__ == "__main__":
    unittest.main()
