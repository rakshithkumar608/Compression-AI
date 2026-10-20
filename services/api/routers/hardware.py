"""
Hardware & Runtime Diagnostics API Router for EcoCompress AI (Phase 3).
"""

from fastapi import APIRouter
from services.hardware_service import get_complete_hardware_diagnostic

router = APIRouter(prefix="/hardware", tags=["Hardware & Runtime"])


@router.get("/diagnostics")
def get_hardware_diagnostics():
    """
    Returns comprehensive verified hardware telemetry, GPU memory headroom,
    driver capability, Python ML runtimes, and storage diagnostics.
    """
    return get_complete_hardware_diagnostic()
