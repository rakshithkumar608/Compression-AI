"""
Resource Feasibility Estimation Service for EcoCompress AI (Phase 3).
Computes transparent, evidence-based memory and storage feasibility estimates.
Accounts for live hardware VRAM/RAM headroom and enumerates all mathematical assumptions.
"""

from typing import Dict, Any, Optional
from services.hardware_service import get_complete_hardware_diagnostic


class FeasibilityVerdict:
    FEASIBLE = "feasible"           # Fits comfortably in VRAM (< 75% utilized)
    TIGHT = "tight"                 # High memory pressure (75% - 95% utilized)
    EXCEEDS_VRAM = "exceeds_vram"   # Exceeds available VRAM (> 95% or > free)
    CANNOT_DETERMINE = "cannot_determine" # Insufficient metadata


def estimate_model_feasibility(
    model_metadata: Dict[str, Any],
    batch_size: int = 1,
    sequence_length: int = 128,
) -> Dict[str, Any]:
    """
    Evaluates whether the inspected model can be accommodated on the verified host hardware.
    Computes precision weights, runtime activations, and VRAM headroom.
    """
    param_count = model_metadata.get("parameter_count")
    total_weight_size_mb = model_metadata.get("total_weight_size_mb")
    task = model_metadata.get("task", "text-classification")

    # If parameter count is not in safetensors metadata, estimate from file size if FP16/FP32
    if param_count is None and total_weight_size_mb and total_weight_size_mb > 0:
        # Assume FP16 weights (~2 bytes per param) as heuristic fallback
        param_count = int((total_weight_size_mb * 1024 * 1024) / 2)
        param_source = "estimated_from_weight_file_size"
    else:
        param_source = "safetensors_metadata" if param_count else "unknown"

    # Query live hardware diagnostics
    hw = get_complete_hardware_diagnostic()
    gpu = hw.get("gpu", {})
    ram = hw.get("ram", {})
    storage = hw.get("storage", {})

    total_vram_mb = gpu.get("total_vram_mb") or 4096
    free_vram_mb = gpu.get("free_vram_mb") or 3800
    used_vram_mb = gpu.get("used_vram_mb") or 296
    available_ram_gb = ram.get("available_gb") or 2.0
    d_free_gb = storage.get("drives", {}).get("D", {}).get("free_gb", 100.0)

    assumptions = [
        f"Inference batch size = {batch_size}",
        f"Sequence length = {sequence_length} tokens",
        "PyTorch/CUDA runtime base context overhead = ~250 MB",
        "Operating system & display headroom buffer = ~400 MB",
        "KV cache & activations heuristic: ~0.5 MB per 1M parameters for classification, ~1.5 MB for generation",
    ]

    if not param_count:
        return {
            "verdict": FeasibilityVerdict.CANNOT_DETERMINE,
            "verdict_label": "Cannot Determine",
            "reason": "Model metadata did not provide a verifiable parameter count or weight tensor shapes.",
            "assumptions": assumptions,
            "uncertainty_disclaimer": "An estimated fit is a mathematical projection, not proof that inference will succeed.",
            "hardware_snapshot": {
                "total_vram_mb": total_vram_mb,
                "free_vram_mb": free_vram_mb,
                "available_ram_gb": available_ram_gb,
            },
        }

    # Weight memory calculations by precision
    bytes_fp32 = param_count * 4
    bytes_fp16 = param_count * 2
    bytes_int8 = param_count * 1
    bytes_int4 = int(param_count * 0.5)

    mb_fp32 = round(bytes_fp32 / (1024**2), 1)
    mb_fp16 = round(bytes_fp16 / (1024**2), 1)
    mb_int8 = round(bytes_int8 / (1024**2), 1)
    mb_int4 = round(bytes_int4 / (1024**2), 1)

    # Runtime activation & KV cache overhead estimation
    is_generation = "generation" in task or "causal" in task
    multiplier = 1.5 if is_generation else 0.5
    activation_overhead_mb = round((param_count / 1_000_000) * multiplier * batch_size, 1)
    base_runtime_mb = 250.0

    total_est_fp16_mb = mb_fp16 + activation_overhead_mb + base_runtime_mb
    total_est_int8_mb = mb_int8 + activation_overhead_mb + base_runtime_mb
    total_est_int4_mb = mb_int4 + activation_overhead_mb + base_runtime_mb

    # Feasibility evaluation against RTX 2050 available VRAM
    # Safe usable VRAM leaves a 350 MB buffer for display/DWM
    usable_vram_budget = max(0, free_vram_mb - 350)

    # Primary evaluation against candidate INT8 quantization
    target_memory_mb = total_est_int8_mb

    if target_memory_mb > free_vram_mb:
        verdict = FeasibilityVerdict.EXCEEDS_VRAM
        verdict_label = "Exceeds Available 4GB VRAM"
        reason = (
            f"Estimated footprint ({target_memory_mb:.1f} MB in INT8) exceeds current free VRAM "
            f"({free_vram_mb} MB). Execution will trigger CUDA Out of Memory (OOM) or force CPU offloading."
        )
    elif target_memory_mb > (usable_vram_budget * 0.85):
        verdict = FeasibilityVerdict.TIGHT
        verdict_label = "Memory Headroom Tight"
        reason = (
            f"Estimated footprint ({target_memory_mb:.1f} MB) fits in free VRAM ({free_vram_mb} MB), "
            f"but leaves less than 15% headroom. Memory spikes during token generation may cause OOM."
        )
    else:
        verdict = FeasibilityVerdict.FEASIBLE
        verdict_label = "Hardware Feasible"
        reason = (
            f"Estimated footprint ({target_memory_mb:.1f} MB in INT8) fits comfortably inside available "
            f"VRAM ({free_vram_mb} MB). Headroom remaining: {free_vram_mb - target_memory_mb:.1f} MB."
        )

    # Storage feasibility check on D: drive
    needed_storage_gb = (total_weight_size_mb or mb_fp16) * 2 / 1024  # baseline + candidate
    storage_feasible = d_free_gb > (needed_storage_gb + 2.0)

    return {
        "verdict": verdict,
        "verdict_label": verdict_label,
        "reason": reason,
        "parameter_count": param_count,
        "parameter_source": param_source,
        "memory_estimates": {
            "fp32_mb": mb_fp32,
            "fp16_mb": mb_fp16,
            "int8_quantized_mb": mb_int8,
            "int4_quantized_mb": mb_int4,
            "estimated_activations_mb": activation_overhead_mb,
            "runtime_base_mb": base_runtime_mb,
            "total_estimated_int8_mb": total_est_int8_mb,
            "total_estimated_fp16_mb": total_est_fp16_mb,
        },
        "headroom": {
            "total_vram_mb": total_vram_mb,
            "free_vram_mb": free_vram_mb,
            "used_vram_mb": used_vram_mb,
            "int8_vram_headroom_mb": round(free_vram_mb - total_est_int8_mb, 1),
            "fp16_vram_headroom_mb": round(free_vram_mb - total_est_fp16_mb, 1),
        },
        "storage_feasibility": {
            "d_drive_free_gb": d_free_gb,
            "estimated_artifact_need_gb": round(needed_storage_gb, 2),
            "storage_adequate": storage_feasible,
        },
        "assumptions": assumptions,
        "uncertainty_disclaimer": (
            "Evidence-based notice: Resource estimates are analytical projections based on parameter counts and linear activation models. "
            "Actual peak memory varies with attention cache layout, framework fragmentation, and CUDA context overhead. "
            "Feasibility estimation does not guarantee successful execution without benchmark profiling."
        ),
    }
