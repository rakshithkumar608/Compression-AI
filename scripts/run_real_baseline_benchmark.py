"""
EcoCompress AI - Real Model Baseline Benchmark Runner
Executes authentic baseline measurement for HuggingFaceTB/SmolLM2-360M-Instruct.
Measures latency, memory, artifact size, and persists genuine metrics to SQLite.
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

from database import init_db, get_db
from schemas import (
    ExperimentCreate,
    ExperimentStatus,
    TaskType,
    OptimizationType,
    WorkloadConfig,
    BenchmarkConfigSchema,
)
from services.benchmark_engine import (
    BenchmarkEngine,
    WorkloadDefinition,
    calculate_latency_statistics,
    _utc_now_iso,
)
from services.experiment_service import ExperimentService


def run_baseline_benchmark():
    print("[EcoCompress Benchmark] Initializing baseline evaluation for SmolLM2-360M-Instruct...")

    db_path = PROJECT_ROOT / "data" / "ecocompress.db"
    init_db(db_path)
    exp_service = ExperimentService(db_path=db_path)

    # 1. Create or retrieve baseline experiment
    exp = exp_service.create_experiment(
        ExperimentCreate(
            name="SmolLM2-360M-Instruct Baseline Run",
            model_id="HuggingFaceTB/SmolLM2-360M-Instruct",
            task=TaskType.TEXT_GENERATION,
            optimization_method=OptimizationType.TORCH_DYNAMIC_INT8,
            workload_config=WorkloadConfig(
                task=TaskType.TEXT_GENERATION,
                dataset="EcoCompress Standard Prompt Suite v1",
                warmup_runs=3,
                measured_runs=10,
                batch_size=1,
                sequence_length=32,
            ),
        )
    )
    print(f"[EcoCompress Benchmark] Created experiment record: {exp.id}")

    # Transition to PROFILING -> BASELINE_RUNNING
    exp_service.transition_status(exp.id, ExperimentStatus.QUEUED)
    exp_service.transition_status(exp.id, ExperimentStatus.VALIDATING)
    exp_service.transition_status(exp.id, ExperimentStatus.PROFILING)
    exp_service.transition_status(exp.id, ExperimentStatus.BASELINE_RUNNING)

    model_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct"
    weights_path = model_dir / "model.safetensors"
    artifact_size_mb = round(weights_path.stat().st_size / (1024 * 1024), 2)
    print(f"[EcoCompress Benchmark] Artifact path: {weights_path}")
    print(f"[EcoCompress Benchmark] Measured artifact size: {artifact_size_mb} MB")

    process = psutil.Process()
    baseline_rss_mb = round(process.memory_info().rss / (1024 * 1024), 2)
    peak_rss_mb = baseline_rss_mb

    print("[EcoCompress Benchmark] Loading model and tokenizer into memory (CPU float32)...")
    t_load_0 = time.perf_counter()
    tokenizer = transformers.AutoTokenizer.from_pretrained(str(model_dir))
    model = transformers.AutoModelForCausalLM.from_pretrained(str(model_dir), torch_dtype=torch.float32)
    model.eval()
    t_load_1 = time.perf_counter()
    print(f"[EcoCompress Benchmark] Model loaded in {t_load_1 - t_load_0:.2f} seconds.")

    mem_after_load = round(process.memory_info().rss / (1024 * 1024), 2)
    if mem_after_load > peak_rss_mb:
        peak_rss_mb = mem_after_load
    print(f"[EcoCompress Benchmark] Memory after load: {mem_after_load} MB (RSS)")

    # Prepare inputs
    prompts = WorkloadDefinition.FIXED_PROMPTS
    tokenized_prompts = [tokenizer(p, return_tensors="pt") for p in prompts]

    # --- Phase 1: Warmup ---
    warmup_count = 3
    print(f"[EcoCompress Benchmark] Running {warmup_count} warmup passes...")
    with torch.no_grad():
        for i in range(warmup_count):
            p = tokenized_prompts[i % len(tokenized_prompts)]
            _ = model.generate(**p, max_new_tokens=32, do_sample=False)
            current_mem = round(process.memory_info().rss / (1024 * 1024), 2)
            if current_mem > peak_rss_mb:
                peak_rss_mb = current_mem
            print(f"  [Warmup {i + 1}/{warmup_count}] completed. RSS: {current_mem} MB")

    # --- Phase 2: Measured Runs ---
    measured_count = 10
    print(f"[EcoCompress Benchmark] Running {measured_count} timed measurement passes...")
    latencies_ms = []

    with torch.no_grad():
        for i in range(measured_count):
            p = tokenized_prompts[i % len(tokenized_prompts)]
            t0 = time.perf_counter_ns()
            _ = model.generate(**p, max_new_tokens=32, do_sample=False)
            t1 = time.perf_counter_ns()

            lat_ms = (t1 - t0) / 1_000_000.0
            latencies_ms.append(lat_ms)

            current_mem = round(process.memory_info().rss / (1024 * 1024), 2)
            if current_mem > peak_rss_mb:
                peak_rss_mb = current_mem
            print(f"  [Measured {i + 1}/{measured_count}] latency: {lat_ms:.2f} ms | RSS: {current_mem} MB")

    stats = calculate_latency_statistics(latencies_ms)
    peak_delta_mb = round(max(0.0, peak_rss_mb - baseline_rss_mb), 2)

    cpu_physical = psutil.cpu_count(logical=False)
    cpu_logical = psutil.cpu_count(logical=True)
    device_str = f"CPU: Intel 12th Gen Core i5 ({cpu_physical} cores / {cpu_logical} threads)"
    runtime_name = f"PyTorch {torch.__version__} / Windows-AMD64"
    recorded_at = _utc_now_iso()

    metadata = {
        "raw_samples_ms": stats.raw_samples_ms,
        "workload_snapshot": WorkloadDefinition.get_standard_workload("text-generation"),
        "limitations": [
            "Executed on CPU: PyTorch runtime is CPU-only (CUDA PyTorch not active).",
            "GPU memory tracking unavailable on CPU runtime.",
            "Energy consumption unavailable: host does not expose an accessible power/RAPL hardware sensor.",
            "Carbon footprint unavailable: requires measured energy sensor readings.",
            "Water consumption unavailable: no validated local datacenter water-use coefficient.",
            "Quality score unavailable in baseline latency pass: requires ground-truth validation dataset.",
        ],
        "notes": "Real baseline benchmark for SmolLM2-360M-Instruct completed successfully.",
        "memory_profile": {
            "baseline_rss_mb": baseline_rss_mb,
            "peak_rss_mb": peak_rss_mb,
            "peak_rss_delta_mb": peak_delta_mb,
            "peak_gpu_mb": None,
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
                exp.id,
                "baseline",
                artifact_size_mb,
                stats.median_ms,
                stats.p95_ms,
                peak_rss_mb,
                None,
                None,
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

        # Update experiment status to COMPLETED (baseline stage)
        conn.execute(
            """
            UPDATE experiments
            SET status = ?, updated_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (ExperimentStatus.COMPLETED.value, recorded_at, recorded_at, exp.id),
        )

    print("\n================ REAL BASELINE BENCHMARK SUMMARY ================")
    print(f"Experiment ID:    {exp.id}")
    print(f"Model ID:         HuggingFaceTB/SmolLM2-360M-Instruct")
    print(f"Revision:         a10cc1512eabd3dde888204e902eca88bddb4951")
    print(f"Artifact Size:    {artifact_size_mb} MB")
    print(f"Median Latency:   {stats.median_ms} ms")
    print(f"P95 Latency:      {stats.p95_ms} ms")
    print(f"Mean Latency:     {stats.mean_ms} ms (Min: {stats.min_ms} ms, Max: {stats.max_ms} ms)")
    print(f"Peak Memory (RSS):{peak_rss_mb} MB (Delta: {peak_delta_mb} MB)")
    print(f"Execution Device: {device_str}")
    print(f"Recorded At:      {recorded_at}")
    print("=================================================================\n")
    return exp.id


if __name__ == "__main__":
    run_baseline_benchmark()
