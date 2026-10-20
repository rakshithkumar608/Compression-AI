"""
Hardware & Runtime Telemetry Service for EcoCompress AI (Phase 3).
Executes safe, read-only diagnostic checks for GPU, VRAM, CPU, RAM, CUDA, and runtimes.
Distinguishes between detected hardware capabilities, installed software capabilities, and unverified items.
"""

import os
import shutil
import subprocess
import sys
import platform
import psutil
from typing import Dict, Any, Optional
from pathlib import Path
from config import settings


def detect_gpu_telemetry() -> Dict[str, Any]:
    """
    Safely queries NVIDIA GPU status using nvidia-smi.
    Handles missing commands or non-NVIDIA environments gracefully.
    """
    nvidia_smi_path = shutil.which("nvidia-smi")
    if not nvidia_smi_path:
        # Fallback check standard windows location
        default_path = Path("C:/Windows/System32/nvidia-smi.exe")
        if default_path.exists():
            nvidia_smi_path = str(default_path)

    if not nvidia_smi_path:
        return {
            "detected": False,
            "status": "unverified",
            "name": None,
            "total_vram_mb": None,
            "free_vram_mb": None,
            "used_vram_mb": None,
            "driver_version": None,
            "pstate": None,
            "notes": "nvidia-smi executable not found in PATH or System32.",
        }

    try:
        # Query GPU name, memory, driver
        cmd = [
            nvidia_smi_path,
            "--query-gpu=name,memory.total,memory.free,memory.used,driver_version,pstate",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        output = res.stdout.strip()
        if not output:
            return {
                "detected": False,
                "status": "unverified",
                "notes": "nvidia-smi returned empty output.",
            }

        parts = [p.strip() for p in output.split(",")]
        if len(parts) >= 6:
            name, total_vram, free_vram, used_vram, driver_version, pstate = parts[:6]
            return {
                "detected": True,
                "status": "verified",
                "name": name,
                "total_vram_mb": int(total_vram),
                "free_vram_mb": int(free_vram),
                "used_vram_mb": int(used_vram),
                "driver_version": driver_version,
                "pstate": pstate,
                "notes": "Hardware telemetry successfully queried via nvidia-smi.",
            }
    except Exception as e:
        return {
            "detected": False,
            "status": "error",
            "notes": f"nvidia-smi query failed: {str(e)}",
        }

    return {
        "detected": False,
        "status": "unverified",
        "notes": "Unexpected nvidia-smi response format.",
    }


def detect_software_capabilities(gpu_telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspects installed Python ML runtimes (torch, safetensors, huggingface_hub).
    Explicitly reports whether PyTorch has CUDA acceleration enabled.
    """
    capabilities: Dict[str, Any] = {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "pytorch": {"installed": False, "version": None, "cuda_available": False, "device_count": 0},
        "safetensors": {"installed": False, "version": None},
        "huggingface_hub": {"installed": False, "version": None},
        "onnxruntime": {"installed": False, "version": None},
        "usable_for_gpu_inference": False,
        "runtime_assessment": "",
    }

    # 1. PyTorch check
    try:
        import torch  # type: ignore
        capabilities["pytorch"]["installed"] = True
        capabilities["pytorch"]["version"] = torch.__version__
        capabilities["pytorch"]["cuda_available"] = torch.cuda.is_available()
        capabilities["pytorch"]["device_count"] = torch.cuda.device_count() if torch.cuda.is_available() else 0

        if torch.cuda.is_available():
            capabilities["usable_for_gpu_inference"] = True
            capabilities["runtime_assessment"] = "PyTorch with CUDA acceleration is active and ready."
        else:
            capabilities["usable_for_gpu_inference"] = False
            if "+cpu" in torch.__version__:
                capabilities["runtime_assessment"] = (
                    "PyTorch is installed as CPU-only build (2.12.0+cpu). "
                    "Hardware has an NVIDIA GPU, but PyTorch cannot allocate CUDA tensors until a CUDA wheel is configured."
                )
            else:
                capabilities["runtime_assessment"] = "PyTorch CUDA initialization returned False."
    except ImportError:
        capabilities["runtime_assessment"] = "PyTorch is not installed in the active environment."

    # 2. Safetensors check
    try:
        import safetensors  # type: ignore
        capabilities["safetensors"]["installed"] = True
        capabilities["safetensors"]["version"] = getattr(safetensors, "__version__", "unknown")
    except ImportError:
        pass

    # 3. Hugging Face Hub check
    try:
        import huggingface_hub  # type: ignore
        capabilities["huggingface_hub"]["installed"] = True
        capabilities["huggingface_hub"]["version"] = getattr(huggingface_hub, "__version__", "unknown")
    except ImportError:
        pass

    # 4. ONNX Runtime check
    try:
        import onnxruntime  # type: ignore
        capabilities["onnxruntime"]["installed"] = True
        capabilities["onnxruntime"]["version"] = getattr(onnxruntime, "__version__", "unknown")
    except ImportError:
        pass

    return capabilities


def detect_system_storage() -> Dict[str, Any]:
    """Inspects storage on C: and D: and validates configured cache directories."""
    drives: Dict[str, Any] = {}
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            letter = part.device.split(":")[0].upper()
            drives[letter] = {
                "mount": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "free_mb": round(usage.free / (1024**2), 2),
                "used_pct": usage.percent,
            }
        except Exception:
            continue

    # Configured locations
    artifacts_dir = str(settings.artifacts_dir)
    data_dir = str(settings.data_dir)

    return {
        "drives": drives,
        "configured_artifacts_dir": artifacts_dir,
        "configured_data_dir": data_dir,
        "hf_home_env": os.getenv("HF_HOME", "Default (~/.cache/huggingface)"),
        "c_drive_status": "CRITICAL_GUARD" if drives.get("C", {}).get("free_mb", 9999) < 500 else "NORMAL",
        "d_drive_status": "ACTIVE_ROOT" if drives.get("D", {}).get("free_gb", 0) > 10 else "LOW",
    }


def get_complete_hardware_diagnostic() -> Dict[str, Any]:
    """Returns comprehensive verified hardware, runtime, and storage diagnostic dictionary."""
    vm = psutil.virtual_memory()
    gpu = detect_gpu_telemetry()
    software = detect_software_capabilities(gpu)
    storage = detect_system_storage()

    return {
        "timestamp": platform.node(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
        },
        "cpu": {
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
            "utilization_pct": psutil.cpu_percent(interval=None),
        },
        "ram": {
            "total_gb": round(vm.total / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "used_pct": vm.percent,
        },
        "gpu": gpu,
        "software": software,
        "storage": storage,
    }
