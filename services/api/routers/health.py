"""
Health & System Diagnostic endpoints for EcoCompress AI API.
"""

from fastapi import APIRouter
from config import settings
from schemas import HealthResponse, SystemSummary, StorageDrive
import platform
import psutil

router = APIRouter(tags=["Health & System"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Returns core API service health and readiness status."""
    return HealthResponse(
        status="healthy",
        phase="Phase 2: API and Experiment Lifecycle",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/system", response_model=SystemSummary)
def get_system():
    """
    Returns read-only hardware telemetry.
    Checks RAM and drives safely without any modifications.
    """
    vm = psutil.virtual_memory()

    storage_info = {}
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            drive_letter = part.device.split(":")[0].upper()
            storage_info[drive_letter] = StorageDrive(
                drive=part.device,
                total_gb=round(usage.total / (1024**3), 2),
                free_gb=round(usage.free / (1024**3), 2),
                free_mb=round(usage.free / (1024**2), 2),
            )
        except Exception:
            continue

    gpu_profile = {
        "model": "NVIDIA GeForce RTX 2050 Laptop GPU",
        "vram_mb": 4096,
        "driver_version": "610.78",
        "cuda_support": "13.3",
        "concurrency_limit": 1,
    }

    return SystemSummary(
        os=platform.system(),
        os_release=platform.release(),
        python_version=platform.python_version(),
        total_ram_gb=round(vm.total / (1024**3), 2),
        free_ram_gb=round(vm.available / (1024**3), 2),
        storage=storage_info,
        gpu_profile=gpu_profile,
    )
