"""
EcoCompress AI - Deterministic Evaluation Scorer (Phase 9B)
Implements objective, transparent scoring rubrics for the 16-item pilot evaluation suite:
- Factual QA (regex and substring matching)
- Simple Reasoning & Arithmetic (numeric extraction and tolerance checks)
- Short Summarization (key concept presence and length penalties)
- Instruction Following (JSON parsing, bullet syntax, single-word choice, line/rhyme rules)
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple


class ItemEvaluationResult:
    """Holds the scoring output and audit trail for a single prompt evaluation."""

    def __init__(
        self,
        item_id: str,
        category: str,
        score: float,
        max_score: float,
        passed: bool,
        explanation: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.item_id = item_id
        self.category = category
        self.score = round(max(0.0, min(score, max_score)), 3)
        self.max_score = round(max_score, 3)
        self.normalized_score = round(self.score / self.max_score, 3) if self.max_score > 0 else 0.0
        self.passed = passed
        self.explanation = explanation
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "score": self.score,
            "max_score": self.max_score,
            "normalized_score": self.normalized_score,
            "passed": self.passed,
            "explanation": self.explanation,
            "details": self.details,
        }


def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts all integers and floating-point numbers from a string."""
    pattern = r"[-+]?\b\d+(?:\.\d+)?\b"
    matches = re.findall(pattern, text)
    nums = []
    for m in matches:
        try:
            nums.append(float(m))
        except ValueError:
            continue
    return nums


def score_item(item: Dict[str, Any], completion: str) -> ItemEvaluationResult:
    """
    Evaluates model completion against the item's rubric.
    Guarantees deterministic, reproducible results with zero non-deterministic LLM judge calls.
    """
    item_id = item["id"]
    category = item["category"]
    rubric = item["rubric"]
    rubric_type = rubric["type"]
    max_score = float(rubric.get("max_score", 1.0))
    cleaned_text = completion.strip()

    # --- Type 1: Regex Match ---
    if rubric_type == "regex_match":
        pattern = rubric["pattern"]
        flags = re.IGNORECASE if not rubric.get("case_sensitive", False) else 0
        match = re.search(pattern, cleaned_text, flags=flags)
        if match:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=max_score,
                max_score=max_score,
                passed=True,
                explanation=f"Matched regex pattern '{pattern}'. Matched string: '{match.group(0)}'.",
                details={"matched_text": match.group(0)},
            )
        else:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation=f"Failed to match regex pattern '{pattern}'.",
                details={"raw_text": cleaned_text},
            )

    # --- Type 2: Substring Match ---
    elif rubric_type == "substring_match":
        pattern = rubric["pattern"]
        flags = re.IGNORECASE if not rubric.get("case_sensitive", False) else 0
        match = re.search(pattern, cleaned_text, flags=flags)
        if match:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=max_score,
                max_score=max_score,
                passed=True,
                explanation=f"Found required substring pattern '{pattern}'. Matched: '{match.group(0)}'.",
                details={"matched_text": match.group(0)},
            )
        else:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation=f"Did not find required substring pattern '{pattern}'.",
                details={"raw_text": cleaned_text},
            )

    # --- Type 3: Numeric Extraction ---
    elif rubric_type == "numeric_extraction":
        expected_val = float(rubric["expected_value"])
        tolerance = float(rubric.get("tolerance", 0.0))
        numbers = extract_numbers_from_text(cleaned_text)

        if not numbers:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation=f"No numerical values found in output. Expected: {expected_val}.",
                details={"extracted_numbers": []},
            )

        # Prefer the last mentioned number (standard for answers like "60 * 3.5 = 210")
        target_candidate = numbers[-1]
        is_match = abs(target_candidate - expected_val) <= tolerance

        # If last number didn't match, check if expected value appears anywhere in numbers
        if not is_match and any(abs(n - expected_val) <= tolerance for n in numbers):
            target_candidate = expected_val
            is_match = True

        if is_match:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=max_score,
                max_score=max_score,
                passed=True,
                explanation=f"Extracted number {target_candidate} matches expected {expected_val} (tolerance {tolerance}).",
                details={"extracted_numbers": numbers, "matched_value": target_candidate},
            )
        else:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation=f"Extracted numbers {numbers} did not match expected {expected_val}.",
                details={"extracted_numbers": numbers},
            )

    # --- Type 4: Concept Presence (Summarization) ---
    elif rubric_type == "concept_presence":
        concept_groups = rubric["required_concept_groups"]
        total_groups = len(concept_groups)
        pts_per_group = max_score / total_groups

        matched_groups = 0
        details_matched = []
        lower_text = cleaned_text.lower()

        for group in concept_groups:
            found = False
            for term in group:
                if term.lower() in lower_text:
                    found = True
                    details_matched.append(term)
                    break
            if found:
                matched_groups += 1

        score = matched_groups * pts_per_group

        # Check sentence or word constraints
        max_sentences = rubric.get("max_sentences")
        if max_sentences:
            sentences = [s for s in re.split(r"[.!?]+", cleaned_text) if s.strip()]
            if len(sentences) > max_sentences:
                score *= 0.8  # 20% penalty for exceeding sentence budget

        max_words = rubric.get("max_words")
        if max_words:
            words = cleaned_text.split()
            if len(words) > max_words:
                score *= 0.8  # 20% penalty for exceeding word budget

        passed = score >= (0.75 * max_score)
        return ItemEvaluationResult(
            item_id=item_id,
            category=category,
            score=round(score, 3),
            max_score=max_score,
            passed=passed,
            explanation=f"Matched {matched_groups}/{total_groups} required concept groups.",
            details={"matched_concepts": details_matched, "raw_text": cleaned_text},
        )

    # --- Type 5: Bullet List Constraint ---
    elif rubric_type == "bullet_list_constraint":
        expected_items = int(rubric["expected_items"])
        prefix = rubric["bullet_prefix"]
        keywords = rubric.get("required_keywords", [])

        lines = [ln.strip() for ln in cleaned_text.splitlines() if ln.strip()]
        bullet_lines = [ln for ln in lines if ln.startswith(prefix) or ln.startswith("*")]

        score = 0.0
        # 1. Bullet count check (0.35 pts)
        if len(bullet_lines) == expected_items:
            score += 0.35
        elif len(lines) == expected_items:
            # Lines match count even if prefix omitted
            score += 0.20

        # 2. Syntax prefix check (0.25 pts)
        if all(ln.startswith(prefix) for ln in bullet_lines) and len(bullet_lines) > 0:
            score += 0.25

        # 3. Required keywords check (0.40 pts)
        lower_text = cleaned_text.lower()
        matched_kw = [kw for kw in keywords if kw.lower() in lower_text]
        if keywords:
            score += 0.40 * (len(matched_kw) / len(keywords))

        passed = score >= 0.85
        return ItemEvaluationResult(
            item_id=item_id,
            category=category,
            score=round(score, 3),
            max_score=max_score,
            passed=passed,
            explanation=f"Bullets: {len(bullet_lines)}/{expected_items}, Keywords matched: {len(matched_kw)}/{len(keywords)}.",
            details={"bullet_lines": bullet_lines, "matched_keywords": matched_kw},
        )

    # --- Type 6: JSON Constraint ---
    elif rubric_type == "json_constraint":
        expected_keys = set(rubric.get("expected_keys", []))
        expected_values = rubric.get("expected_values", {})

        # Strip markdown code blocks if present
        json_str = cleaned_text
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                return ItemEvaluationResult(
                    item_id=item_id,
                    category=category,
                    score=0.2,
                    max_score=max_score,
                    passed=False,
                    explanation="Output is valid JSON but not a JSON object/dictionary.",
                    details={"parsed": parsed},
                )

            # Check keys
            parsed_keys = set(parsed.keys())
            if parsed_keys != expected_keys:
                return ItemEvaluationResult(
                    item_id=item_id,
                    category=category,
                    score=0.5,
                    max_score=max_score,
                    passed=False,
                    explanation=f"JSON parsed but keys {parsed_keys} do not match expected {expected_keys}.",
                    details={"parsed": parsed},
                )

            # Check values
            all_values_match = True
            for k, expected_v in expected_values.items():
                if parsed.get(k) != expected_v:
                    all_values_match = False
                    break

            if all_values_match:
                return ItemEvaluationResult(
                    item_id=item_id,
                    category=category,
                    score=max_score,
                    max_score=max_score,
                    passed=True,
                    explanation="Valid JSON parsed with exact required keys and values.",
                    details={"parsed": parsed},
                )
            else:
                return ItemEvaluationResult(
                    item_id=item_id,
                    category=category,
                    score=0.75,
                    max_score=max_score,
                    passed=False,
                    explanation="Valid JSON with matching keys, but values differed from expected.",
                    details={"parsed": parsed, "expected": expected_values},
                )

        except Exception as e:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation=f"Failed to parse as valid JSON: {e}",
                details={"raw_text": cleaned_text},
            )

    # --- Type 7: Single Word Choice ---
    elif rubric_type == "single_word_choice":
        expected_choice = rubric["expected_choice"].strip().lower()
        allowed = [c.lower() for c in rubric.get("allowed_choices", [])]

        # Extract first alphanumeric word
        words = re.findall(r"\b[A-Za-z]+\b", cleaned_text)
        if not words:
            return ItemEvaluationResult(
                item_id=item_id,
                category=category,
                score=0.0,
                max_score=max_score,
                passed=False,
                explanation="No words found in output.",
                details={"raw_text": cleaned_text},
            )

        first_word = words[0].lower()
        is_exact = first_word == expected_choice

        # Check single-word constraint
        if is_exact and len(words) == 1:
            score = max_score
            passed = True
            expl = f"Exact single-word output: '{words[0]}'."
        elif is_exact:
            score = 0.7 * max_score
            passed = True
            expl = f"Correct word '{words[0]}' but output contained additional words ({len(words)} total)."
        else:
            score = 0.0
            passed = False
            expl = f"Output word '{first_word}' does not match expected '{expected_choice}'."

        return ItemEvaluationResult(
            item_id=item_id,
            category=category,
            score=round(score, 3),
            max_score=max_score,
            passed=passed,
            explanation=expl,
            details={"words": words},
        )

    # --- Type 8: Rhyme Line Constraint ---
    elif rubric_type == "rhyme_line_constraint":
        expected_lines = int(rubric["expected_lines"])
        line1_end = rubric["line1_end"].lower()
        line2_end = rubric["line2_end"].lower()

        lines = [ln.strip() for ln in cleaned_text.splitlines() if ln.strip()]
        score = 0.0

        if len(lines) == expected_lines:
            score += 0.4
        elif len(lines) > 0:
            score += 0.2

        if len(lines) >= 1:
            last_word_l1 = re.findall(r"\b[A-Za-z]+\b", lines[0])
            if last_word_l1 and last_word_l1[-1].lower() == line1_end:
                score += 0.3

        if len(lines) >= 2:
            last_word_l2 = re.findall(r"\b[A-Za-z]+\b", lines[1])
            if last_word_l2 and last_word_l2[-1].lower() == line2_end:
                score += 0.3

        passed = score >= 0.85
        return ItemEvaluationResult(
            item_id=item_id,
            category=category,
            score=round(score, 3),
            max_score=max_score,
            passed=passed,
            explanation=f"Line count: {len(lines)}/{expected_lines}, score: {score:.2f}.",
            details={"lines": lines},
        )

    else:
        # Fallback unknown rubric
        return ItemEvaluationResult(
            item_id=item_id,
            category=category,
            score=0.0,
            max_score=max_score,
            passed=False,
            explanation=f"Unknown rubric type '{rubric_type}'.",
            details={},
        )
