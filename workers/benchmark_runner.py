"""
EcoCompress AI - Background Benchmark Worker Runner (Phase 4)
Decoupled command-line and process runner for baseline and candidate benchmarks.
Executes benchmarks outside the FastAPI server process without blocking HTTP requests.
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root and services/api to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

from database import init_db
from schemas import BenchmarkConfigSchema
from services.benchmark_engine import BenchmarkEngine, BenchmarkCancelledError, BenchmarkExecutionError


def run_worker(
    experiment_id: str,
    synthetic: bool = True,
    warmup: int = 5,
    measured: int = 20,
    target_device: str = "cpu",
    db_path: Path | str | None = None,
) -> int:
    """
    Executes a benchmark run for the specified experiment ID.
    Decoupled from HTTP requests.
    """
    print(f"[EcoCompress Worker] Starting benchmark for experiment: {experiment_id}")
    print(f"[EcoCompress Worker] Configuration: {warmup} warmup, {measured} measured, target: {target_device}")

    # Ensure database is initialized
    init_db(db_path)

    # Validate that experiment exists before executing benchmark
    from database import get_db
    from schemas import ExperimentStatus
    with get_db(db_path) as conn:
        cur = conn.execute("SELECT id, status FROM experiments WHERE id = ?", (experiment_id,))
        row = cur.fetchone()
        if not row:
            print(f"[EcoCompress Worker] Error: Experiment '{experiment_id}' does not exist in the database.")
            print(f"[EcoCompress Worker] Create the experiment via the API or frontend before dispatching the worker.")
            return 1
        if row["status"] in [ExperimentStatus.COMPLETED.value, ExperimentStatus.CANCELLED.value]:
            print(f"[EcoCompress Worker] Notice: Experiment '{experiment_id}' is already in terminal state '{row['status']}'.")

    engine = BenchmarkEngine(db_path=db_path)
    config = BenchmarkConfigSchema(
        warmup_runs=warmup,
        measured_runs=measured,
        target_device=target_device,
    )

    def progress_callback(step: str, pct: int):
        print(f"[{pct:3d}%] {step}")

    try:
        if synthetic:
            print("[EcoCompress Worker] Executing synthetic baseline benchmark...")
            res = engine.run_synthetic_benchmark(
                experiment_id=experiment_id,
                config=config,
                progress_callback=progress_callback,
            )
            print("[EcoCompress Worker] Benchmark completed successfully.")
            print(f"  - Median Latency: {res.latency.median_ms} ms")
            print(f"  - P95 Latency:    {res.latency.p95_ms} ms")
            print(f"  - Peak Memory:    {res.memory.peak_rss_mb} MB (Delta: {res.memory.peak_rss_delta_mb} MB)")
            print(f"  - Device:         {res.hardware_device}")
            print(f"  - Limitations:    {len(res.limitations)} explicit items noted")
            return 0
        else:
            print("[EcoCompress Worker] Real model benchmarking requires explicit model approval.")
            return 1
    except BenchmarkCancelledError as ce:
        print(f"[EcoCompress Worker] Benchmark cancelled: {ce}")
        return 130
    except BenchmarkExecutionError as ee:
        print(f"[EcoCompress Worker] Benchmark execution error: {ee}")
        return 1
    except Exception as e:
        print(f"[EcoCompress Worker] Unexpected error: {e}")
        return 2


def main():
    parser = argparse.ArgumentParser(description="EcoCompress AI Benchmark Runner")
    parser.add_argument("--experiment-id", required=True, help="Target experiment identifier")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Run synthetic benchmark workload")
    parser.add_argument("--warmup", type=int, default=5, help="Warmup iterations (default: 5)")
    parser.add_argument("--measured", type=int, default=20, help="Measured iterations (default: 20)")
    parser.add_argument("--device", type=str, default="cpu", help="Target device (default: cpu)")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite database path")

    args = parser.parse_args()
    code = run_worker(
        experiment_id=args.experiment_id,
        synthetic=args.synthetic,
        warmup=args.warmup,
        measured=args.measured,
        target_device=args.device,
        db_path=args.db_path,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
