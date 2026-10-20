"""
EcoCompress AI - FastAPI Backend Service (Phase 1 Foundation)
Provides service health and safe hardware runtime diagnostics.
Long-running model benchmarks are strictly decoupled from HTTP request loops.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import platform
import psutil

app = FastAPI(
    title="EcoCompress AI API",
    description="Evidence-based model compression and evaluation API",
    version="0.1.0",
)

# Enable CORS for local Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    phase: str
    service: str


class StorageSummary(BaseModel):
    drive: str
    total_gb: float
    free_gb: float
    free_mb: float


class SystemSummary(BaseModel):
    os: str
    os_release: str
    python_version: str
    total_ram_gb: float
    free_ram_gb: float
    storage: Dict[str, StorageSummary]
    gpu_profile: Dict[str, Any]


@app.get("/health", response_model=HealthResponse)
def get_health():
    """Returns basic service health status."""
    return HealthResponse(
        status="healthy",
        phase="Phase 1 Foundation",
        service="EcoCompress AI Core API",
    )


@app.get("/system", response_model=SystemSummary)
def get_system_diagnostics():
    """
    Returns read-only hardware telemetry.
    Checks RAM and drives safely without any system modifications.
    """
    vm = psutil.virtual_memory()

    storage_info: Dict[str, StorageSummary] = {}
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            drive_letter = part.device.split(":")[0].upper()
            storage_info[drive_letter] = StorageSummary(
                drive=part.device,
                total_gb=round(usage.total / (1024**3), 2),
                free_gb=round(usage.free / (1024**3), 2),
                free_mb=round(usage.free / (1024**2), 2),
            )
        except Exception:
            continue

    # NVIDIA RTX 2050 profile detected in Phase 0
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
