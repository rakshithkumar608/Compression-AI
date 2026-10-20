"""
EcoCompress AI - Real Model Quantization Execution
Quantizes HuggingFaceTB/SmolLM2-360M-Instruct to INT8 on CPU using PyTorch Dynamic INT8.
Writes candidate artifact to D:/Projects/Compression AI/artifacts/SmolLM2-360M-Instruct-int8.
"""

import sys
import time
from pathlib import Path

# Add project root and services/api to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

from services.quantization_service import (
    QuantizationConfig,
    QuantizationPipeline,
    QuantizationResult,
)


def run_quantization():
    source_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct"
    output_dir = PROJECT_ROOT / "artifacts" / "SmolLM2-360M-Instruct-int8"

    print("[EcoCompress Quantizer] Initializing Phase 5 Quantization Pipeline...")
    print(f"  - Source Model:      {source_dir}")
    print(f"  - Target Candidate:  {output_dir}")
    print(f"  - Method:            torch-dynamic-int8 (Linear weights -> INT8)")

    config = QuantizationConfig(
        source_model_path=source_dir,
        output_dir=output_dir,
        quantization_method="torch-dynamic-int8",
        expected_revision="a10cc1512eabd3dde888204e902eca88bddb4951",
        min_disk_headroom_gb=2.0,
    )

    pipeline = QuantizationPipeline()

    def progress_callback(step: str, pct: int):
        print(f"[{pct:3d}%] {step}")

    t0 = time.perf_counter()
    res: QuantizationResult = pipeline.quantize_model(
        config=config,
        progress_callback=progress_callback,
    )
    t1 = time.perf_counter()

    print("\n================ REAL MODEL QUANTIZATION SUMMARY ================")
    print(f"Source Model:         {res.source_model}")
    print(f"Output Directory:     {res.output_directory}")
    print(f"Quantization Method:  {res.quantization_method}")
    print(f"Precision:            {res.precision}")
    print(f"Source Revision:      {res.source_revision}")
    print(f"Original Size:        {res.original_size_mb} MB")
    print(f"Quantized Size:       {res.quantized_size_mb} MB")
    print(f"Size Reduction:       -{res.compression_ratio_pct}%")
    print(f"Quantized Layers:     {res.quantized_layers_count} linear layers")
    print(f"Artifact Files:       {', '.join(res.output_files)}")
    print(f"Conversion Duration:  {res.duration_seconds} seconds")
    print(f"Created At:           {res.created_at}")
    print("=================================================================\n")
    return res


if __name__ == "__main__":
    run_quantization()
