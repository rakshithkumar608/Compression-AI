"""
EcoCompress AI - Phase 9C: SRA-04 Token Budget Diagnostic Investigation
Performs a controlled, isolated investigation into item SRA-04 (sequence: 2, 4, 8, 16, ...)
evaluating both baseline (FP32) and candidate (INT8 storage) models under:
1. Original condition: max_new_tokens = 16 (confirming reproducibility)
2. Retest condition:   max_new_tokens = 32 (investigating token budget ceiling)
3. Extended condition: max_new_tokens = 64 (full generative sequence observation)

Strict isolation, CPU-only execution, zero network access, pre/post hash verification.
"""

import gc
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root and services/api to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

import psutil
import torch
import transformers
import safetensors.torch

from services.evaluation_scorer import score_item

EXPECTED_BASELINE_HASH = "e6bffe7435d7ddc10fd3b9a9efd429dafbacb1cb17015fb5562664e7532bf86e"
EXPECTED_CANDIDATE_HASH = "0d0a79057e4ddacf965c40d9998e200f00d89e28e3f6bb7ca45903ed54f6a064"
EXPECTED_EXPORT_ZIP_HASH = "c450fdf7a67a660260a4fafcbac8b45dbc840363a86b06d4393e22cd7e761150"

SRA04_ITEM = {
    "id": "SRA-04",
    "category": "simple_reasoning",
    "prompt": "What is the next number in the sequence: 2, 4, 8, 16, ...? State only the next number.",
    "reference_answer": "32",
    "rubric": {
        "type": "numeric_extraction",
        "expected_value": 32.0,
        "tolerance": 0.0,
        "max_score": 1.0,
        "description": "Next sequence number must be 32.",
    },
}


def compute_file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()


def run_single_inference(model, tokenizer, item: Dict[str, Any], max_new_tokens: int) -> Dict[str, Any]:
    process = psutil.Process()
    chat_prompt = f"<|im_start|>user\n{item['prompt']}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(chat_prompt, return_tensors="pt")
    input_len = inputs["input_ids"].shape[1]

    t0 = time.perf_counter_ns()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            pad_token_id=tokenizer.eos_token_id,
        )
    t1 = time.perf_counter_ns()

    dur_ms = (t1 - t0) / 1e6
    dur_s = dur_ms / 1000.0

    out_tokens = out[0].tolist()
    generated_ids = out_tokens[input_len:]
    gen_token_count = len(generated_ids)

    raw_completion = tokenizer.decode(generated_ids, skip_special_tokens=False)
    clean_completion = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    # Determine finish reason
    reached_eos = tokenizer.eos_token_id in generated_ids
    if reached_eos:
        finish_reason = "eos_token"
    elif gen_token_count >= max_new_tokens:
        finish_reason = "max_tokens_reached"
    else:
        finish_reason = "stop_condition"

    # Score output
    eval_res = score_item(item, clean_completion)
    rss_mb = round(process.memory_info().rss / (1024 * 1024), 2)

    return {
        "max_new_tokens_setting": max_new_tokens,
        "generated_token_count": gen_token_count,
        "latency_ms": round(dur_ms, 2),
        "throughput_tps": round(gen_token_count / dur_s, 2) if dur_s > 0 else 0.0,
        "reached_eos": reached_eos,
        "finish_reason": finish_reason,
        "raw_completion": raw_completion,
        "clean_completion": clean_completion,
        "score": eval_res.score,
        "passed": eval_res.passed,
        "explanation": eval_res.explanation,
        "extracted_details": eval_res.details,
        "rss_mb": rss_mb,
    }


def main():
    print("=== [PHASE 9C: SRA-04 TOKEN BUDGET DIAGNOSTIC] ===")
    base_file = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct" / "model.safetensors"
    cand_file = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct-int8" / "model.safetensors"
    zip_file = PROJECT_ROOT / "exports" / "export_exp-20261020102101-4f000a_int8.zip"

    # Preflight hashes
    print("Preflight artifact hash checks...")
    h_b_pre = compute_file_sha256(base_file)
    h_c_pre = compute_file_sha256(cand_file)
    h_z_pre = compute_file_sha256(zip_file)
    assert h_b_pre == EXPECTED_BASELINE_HASH, "Baseline hash mismatch!"
    assert h_c_pre == EXPECTED_CANDIDATE_HASH, "Candidate hash mismatch!"
    assert h_z_pre == EXPECTED_EXPORT_ZIP_HASH, "Export zip hash mismatch!"
    print("Preflight hashes verified 100% bit-identical.")

    token_budgets = [16, 32, 64]
    results: Dict[str, Any] = {
        "investigation_id": "phase9c_sra04_token_budget",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "target_prompt": SRA04_ITEM["prompt"],
        "expected_answer": SRA04_ITEM["reference_answer"],
        "rubric": SRA04_ITEM["rubric"],
        "token_budgets_tested": token_budgets,
        "baseline_runs": {},
        "candidate_runs": {},
    }

    # 1. Baseline Evaluation
    print("\n--- [Loading Baseline FP32 Model] ---")
    base_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct"
    b_tok = transformers.AutoTokenizer.from_pretrained(str(base_dir), local_files_only=True)
    b_model = transformers.AutoModelForCausalLM.from_pretrained(
        str(base_dir), torch_dtype=torch.float32, local_files_only=True
    )
    b_model.eval()

    # Warmup
    print("[Baseline] Warmup pass...")
    _ = run_single_inference(b_model, b_tok, SRA04_ITEM, max_new_tokens=16)

    print("[Baseline] Executing diagnostic token budget tests...")
    for tb in token_budgets:
        res = run_single_inference(b_model, b_tok, SRA04_ITEM, max_new_tokens=tb)
        results["baseline_runs"][f"tokens_{tb}"] = res
        print(f"  [Baseline max_tokens={tb:2d}]: tokens={res['generated_token_count']:2d} | "
              f"lat={res['latency_ms']:7.2f} ms | score={res['score']:.1f} | "
              f"eos={res['reached_eos']} | reason={res['finish_reason']}")
        print(f"    Output: {repr(res['clean_completion'])}")

    del b_model, b_tok
    gc.collect()

    # 2. Candidate Evaluation
    print("\n--- [Loading Candidate INT8-Storage Model] ---")
    cand_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct-int8"
    c_tok = transformers.AutoTokenizer.from_pretrained(str(cand_dir), local_files_only=True)
    c_model = transformers.AutoModelForCausalLM.from_pretrained(
        str(cand_dir), torch_dtype=torch.float32, local_files_only=True
    )
    weights_path = cand_dir / "model.safetensors"
    state = safetensors.torch.load_file(str(weights_path))

    reconstructed = 0
    for name, module in c_model.named_modules():
        if isinstance(module, torch.nn.Linear):
            w_name = f"{name}.weight"
            scale_name = f"{w_name}_scale"
            zp_name = f"{w_name}_zero_point"
            if w_name in state and scale_name in state:
                scale = state[scale_name].item()
                zp = state[zp_name].item()
                w_int8 = state[w_name]
                w_dequant = (w_int8.to(torch.float32) - zp) * scale
                module.weight.data = w_dequant.to(module.weight.dtype)
                reconstructed += 1
    c_model.eval()
    print(f"[Candidate] Dequantized {reconstructed} layers to FP32 in RAM.")

    # Warmup
    print("[Candidate] Warmup pass...")
    _ = run_single_inference(c_model, c_tok, SRA04_ITEM, max_new_tokens=16)

    print("[Candidate] Executing diagnostic token budget tests...")
    for tb in token_budgets:
        res = run_single_inference(c_model, c_tok, SRA04_ITEM, max_new_tokens=tb)
        results["candidate_runs"][f"tokens_{tb}"] = res
        print(f"  [Candidate max_tokens={tb:2d}]: tokens={res['generated_token_count']:2d} | "
              f"lat={res['latency_ms']:7.2f} ms | score={res['score']:.1f} | "
              f"eos={res['reached_eos']} | reason={res['finish_reason']}")
        print(f"    Output: {repr(res['clean_completion'])}")

    del c_model, c_tok
    gc.collect()

    # Post-run hash verification
    print("\nPost-test artifact hash checks...")
    h_b_post = compute_file_sha256(base_file)
    h_c_post = compute_file_sha256(cand_file)
    h_z_post = compute_file_sha256(zip_file)
    assert h_b_post == EXPECTED_BASELINE_HASH, "Baseline mutated during test!"
    assert h_c_post == EXPECTED_CANDIDATE_HASH, "Candidate mutated during test!"
    assert h_z_post == EXPECTED_EXPORT_ZIP_HASH, "Export zip mutated during test!"
    print("Post-test artifact hashes verified 100% bit-identical.")

    # Save results JSON
    out_file = PROJECT_ROOT / "data" / "eval_results" / "investigation_sra04_token_budget.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[Phase 9C Investigation Complete] Saved results to: {out_file}\n")


if __name__ == "__main__":
    main()
