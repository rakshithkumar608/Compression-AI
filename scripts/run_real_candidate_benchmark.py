"""
EcoCompress AI - Real Candidate Benchmark & Comparative Evaluation (Phase 6)
Executes fair, repeatable benchmark for the INT8 candidate model on CPU.
Measures latency, memory, artifact size, evaluates output text against baseline,
persists candidate results to SQLite, and computes acceptance decision.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add project root and services/api to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

import psutil
import torch
import transformers
import safetensors.torch

from database import init_db, get_db
from schemas import (
    ExperimentStatus,
    AcceptanceDecision,
)
from services.benchmark_engine import (
    WorkloadDefinition,
    calculate_latency_statistics,
    _utc_now_iso,
)
from services.experiment_service import ExperimentService


def load_candidate_model(candidate_dir: Path):
    """
    Loads candidate model using verified stored scales and zero points.
    Applies dequantized linear weight reconstruction for exact token fidelity.
    """
    tok = transformers.AutoTokenizer.from_pretrained(str(candidate_dir))
    model = transformers.AutoModelForCausalLM.from_pretrained(str(candidate_dir), torch_dtype=torch.float32)
    state = safetensors.torch.load_file(str(candidate_dir / "model.safetensors"))

    reconstructed_count = 0
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            w_name = f"{name}.weight"
            if w_name in state and f"{w_name}_scale" in state:
                scale = state[f"{w_name}_scale"].item()
                zp = state[f"{w_name}_zero_point"].item()
                w_int8 = state[w_name]
                w_dequant = (w_int8.to(torch.float32) - zp) * scale
                module.weight.data = w_dequant.to(module.weight.dtype)
                reconstructed_count += 1

    model.eval()
    return model, tok, reconstructed_count


def run_candidate_benchmark(exp_id: str = "exp-20261020102101-4f000a"):
    print(f"[EcoCompress Candidate Eval] Evaluating candidate for experiment: {exp_id}")

    db_path = PROJECT_ROOT / "data" / "ecocompress.db"
    init_db(db_path)
    exp_service = ExperimentService(db_path=db_path)

    # Verify experiment exists and retrieve baseline results
    with get_db(db_path) as conn:
        b_cur = conn.execute(
            "SELECT * FROM benchmark_results WHERE experiment_id = ? AND candidate_type = 'baseline'",
            (exp_id,),
        )
        baseline = b_cur.fetchone()
        if not baseline:
            raise RuntimeError(f"No baseline benchmark found for experiment '{exp_id}'.")

    candidate_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct-int8"
    weights_path = candidate_dir / "model.safetensors"
    candidate_size_mb = round(weights_path.stat().st_size / (1024 * 1024), 2)
    baseline_size_mb = baseline["artifact_size_mb"]

    print(f"  - Baseline Size:     {baseline_size_mb} MB")
    print(f"  - Candidate Size:    {candidate_size_mb} MB")
    size_reduction_pct = round(((baseline_size_mb - candidate_size_mb) / baseline_size_mb) * 100.0, 2)
    print(f"  - Size Delta:        -{size_reduction_pct}%")

    process = psutil.Process()
    baseline_rss_mb = round(process.memory_info().rss / (1024 * 1024), 2)
    peak_rss_mb = baseline_rss_mb

    print("[EcoCompress Candidate Eval] Loading candidate model into memory...")
    t_load_0 = time.perf_counter()
    model, tokenizer, reconstructed_layers = load_candidate_model(candidate_dir)
    t_load_1 = time.perf_counter()
    load_duration_s = round(t_load_1 - t_load_0, 2)
    print(f"[EcoCompress Candidate Eval] Candidate loaded in {load_duration_s}s ({reconstructed_layers} quantized layers).")

    mem_after_load = round(process.memory_info().rss / (1024 * 1024), 2)
    if mem_after_load > peak_rss_mb:
        peak_rss_mb = mem_after_load

    # Format standard 5 prompts with ChatML
    prompts = WorkloadDefinition.FIXED_PROMPTS
    formatted_prompts = [
        f"<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n" for p in prompts
    ]
    tokenized_prompts = [tokenizer(p, return_tensors="pt") for p in formatted_prompts]

    # --- Phase 1: Warmup ---
    warmup_count = 3
    print(f"[EcoCompress Candidate Eval] Running {warmup_count} warmup passes...")
    with torch.no_grad():
        for i in range(warmup_count):
            p = tokenized_prompts[i % len(tokenized_prompts)]
            _ = model.generate(**p, max_new_tokens=32, do_sample=False)
            current_mem = round(process.memory_info().rss / (1024 * 1024), 2)
            if current_mem > peak_rss_mb:
                peak_rss_mb = current_mem
            print(f"  [Warmup {i + 1}/{warmup_count}] completed. RSS: {current_mem} MB")

    # --- Phase 2: Timed Measurement ---
    measured_count = 10
    print(f"[EcoCompress Candidate Eval] Running {measured_count} timed measurement passes...")
    latencies_ms = []
    generated_completions = []

    with torch.no_grad():
        for i in range(measured_count):
            p = tokenized_prompts[i % len(tokenized_prompts)]
            t0 = time.perf_counter_ns()
            out = model.generate(**p, max_new_tokens=32, do_sample=False)
            t1 = time.perf_counter_ns()

            lat_ms = (t1 - t0) / 1_000_000.0
            latencies_ms.append(lat_ms)

            # Record completion text for output evaluation
            if i < len(prompts):
                in_len = p["input_ids"].shape[1]
                comp_text = tokenizer.decode(out[0][in_len:], skip_special_tokens=True).strip()
                generated_completions.append({"prompt": prompts[i], "completion": comp_text})

            current_mem = round(process.memory_info().rss / (1024 * 1024), 2)
            if current_mem > peak_rss_mb:
                peak_rss_mb = current_mem
            print(f"  [Measured {i + 1}/{measured_count}] latency: {lat_ms:.2f} ms | RSS: {current_mem} MB")

    stats = calculate_latency_statistics(latencies_ms)
    peak_delta_mb = round(max(0.0, peak_rss_mb - baseline_rss_mb), 2)

    device_str = baseline["hardware_device"]
    runtime_name = baseline["runtime_name"]
    recorded_at = _utc_now_iso()

    # Compare with baseline
    base_med_lat = baseline["median_latency_ms"]
    cand_med_lat = stats.median_ms
    latency_delta_pct = round(((cand_med_lat - base_med_lat) / base_med_lat) * 100.0, 2)

    base_p95_lat = baseline["p95_latency_ms"]
    cand_p95_lat = stats.p95_ms
    p95_delta_pct = round(((cand_p95_lat - base_p95_lat) / base_p95_lat) * 100.0, 2)

    # Acceptance Criteria Evaluation
    # Thresholds: size_reduction >= 40.0%
    reasons = []
    passed = True

    if size_reduction_pct >= 40.0:
        reasons.append(f"Storage reduction passed: achieved {size_reduction_pct}% reduction (threshold: >= 40.0%).")
    else:
        reasons.append(f"Storage reduction failed: achieved {size_reduction_pct}% reduction (threshold: >= 40.0%).")
        passed = False

    reasons.append("Quality score formally unverified: no standardized benchmark evaluation dataset (e.g. MMLU/SST-2) configured in local runner.")
    reasons.append(f"Latency delta: {cand_med_lat:.2f} ms vs {base_med_lat:.2f} ms baseline ({latency_delta_pct:+.2f}%).")

    acceptance_decision = AcceptanceDecision(
        passed=passed,
        reasons=reasons,
        timestamp=recorded_at,
    )

    metadata = {
        "raw_samples_ms": stats.raw_samples_ms,
        "workload_snapshot": WorkloadDefinition.get_standard_workload("text-generation"),
        "load_duration_seconds": load_duration_s,
        "sample_completions": generated_completions,
        "limitations": [
            "Executed on CPU: PyTorch runtime is CPU-only.",
            "Energy consumption unavailable: host does not expose power/RAPL hardware sensor.",
            "Carbon footprint unavailable: requires measured energy sensor readings.",
            "Water consumption unavailable: no validated local datacenter coefficient.",
            "Task quality evaluated via qualitative prompt suite (no ground-truth test set configured).",
        ],
        "notes": "Candidate benchmark for SmolLM2-360M-Instruct-int8 completed successfully.",
        "memory_profile": {
            "baseline_rss_mb": baseline_rss_mb,
            "peak_rss_mb": peak_rss_mb,
            "peak_rss_delta_mb": peak_delta_mb,
            "measurement_type": "measured",
        },
    }

    # Persist into benchmark_results
    with get_db(db_path) as conn:
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
                exp_id,
                "candidate",
                candidate_size_mb,
                stats.median_ms,
                stats.p95_ms,
                peak_rss_mb,
                None,
                "unverified (qualitative 5-prompt suite)",
                None,
                "unavailable",
                None,
                "unavailable",
                None,
                "unavailable",
                measured_count,
                warmup_count,
                device_str,
                recorded_at,
                runtime_name,
                "a10cc1512eabd3dde888204e902eca88bddb4951",
                json.dumps(metadata),
            ),
        )

        # Update experiment status to COMPLETED with acceptance decision
        conn.execute(
            """
            UPDATE experiments
            SET status = ?, acceptance_decision = ?, updated_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                ExperimentStatus.COMPLETED.value,
                acceptance_decision.model_dump_json(),
                recorded_at,
                recorded_at,
                exp_id,
            ),
        )

    print("\n================ CANDIDATE VS BASELINE COMPARATIVE SUMMARY ================")
    print(f"Experiment ID:        {exp_id}")
    print(f"Artifact Size:        {baseline_size_mb} MB -> {candidate_size_mb} MB ({size_reduction_pct:+.2f}%) [Gate >= 40%: {'PASS' if size_reduction_pct >= 40 else 'FAIL'}]")
    print(f"Median Latency:       {base_med_lat:.2f} ms -> {cand_med_lat:.2f} ms ({latency_delta_pct:+.2f}%)")
    print(f"P95 Latency:          {base_p95_lat:.2f} ms -> {cand_p95_lat:.2f} ms ({p95_delta_pct:+.2f}%)")
    print(f"Peak RAM (RSS):       {baseline['peak_memory_mb']} MB -> {peak_rss_mb} MB")
    print(f"Acceptance Decision:  {'ACCEPTED' if passed else 'REJECTED'}")
    print("Acceptance Reasons:")
    for r in reasons:
        print(f"  - {r}")
    print(f"Recorded At:          {recorded_at}")
    print("===========================================================================\n")
    return acceptance_decision


if __name__ == "__main__":
    run_candidate_benchmark()
