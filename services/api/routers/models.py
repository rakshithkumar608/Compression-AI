"""
Safe Model Inspection Router for EcoCompress AI (Phase 3).
Inspects Hugging Face repositories and approved local directories.
Computes resource feasibility without downloading weight tensors.
"""

from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.model_inspector import (
    inspect_huggingface_model,
    inspect_local_model,
    ModelInspectionError,
)
from services.feasibility_service import estimate_model_feasibility

router = APIRouter(prefix="/models", tags=["Model Inspection"])


class ModelInspectRequest(BaseModel):
    source: Literal["huggingface", "local"] = "huggingface"
    model_id: str = Field(..., min_length=2, max_length=250, description="Hugging Face repo ID or approved local directory path")
    revision: Optional[str] = Field(default=None, max_length=100, description="Optional Git revision hash or branch")
    batch_size: int = Field(default=1, ge=1, le=64)
    sequence_length: int = Field(default=128, ge=8, le=4096)


@router.post(
    "/inspect",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Malformed model ID or unsafe path"},
        403: {"description": "Gated/private model or unauthorized directory"},
        404: {"description": "Model repository or local directory not found"},
    },
)
def inspect_model(payload: ModelInspectRequest):
    """
    Safely inspects model metadata, formats, parameter counts, and licenses.
    Evaluates hardware VRAM and storage feasibility on the host system.
    Strictly read-only: does NOT download weight files or execute code.
    """
    try:
        if payload.source == "huggingface":
            metadata = inspect_huggingface_model(payload.model_id, revision=payload.revision)
        elif payload.source == "local":
            metadata = inspect_local_model(payload.model_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid source: must be 'huggingface' or 'local'.")

        # Run Resource Feasibility Estimator against verified host hardware
        feasibility = estimate_model_feasibility(
            model_metadata=metadata,
            batch_size=payload.batch_size,
            sequence_length=payload.sequence_length,
        )

        return {
            "status": "success",
            "metadata": metadata,
            "feasibility": feasibility,
        }

    except ModelInspectionError as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if e.code == "MODEL_NOT_FOUND" or e.code == "LOCAL_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        elif e.code in ["GATED_OR_PRIVATE", "UNAPPROVED_DIRECTORY"]:
            status_code = status.HTTP_403_FORBIDDEN
        elif e.code == "NETWORK_TIMEOUT":
            status_code = status.HTTP_504_GATEWAY_TIMEOUT

        raise HTTPException(
            status_code=status_code,
            detail={
                "message": e.message,
                "code": e.code,
                "details": e.details,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during model inspection: {str(e)}",
        )
