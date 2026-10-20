"""
Export and verification endpoints for EcoCompress AI API.
Provides endpoints to create reproducible export bundles, inspect manifests,
and verify file integrity via SHA-256 checksums.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from config import settings
from schemas import (
    ErrorResponse,
    ExportPackageResponse,
    ExportVerifyRequest,
    ExportVerifyResponse,
)
from services.export_service import (
    ExportService,
    ExportPreflightError,
    ExportVerificationError,
    compute_file_sha256,
)

router = APIRouter(prefix="", tags=["Exports"])
export_service = ExportService()


@router.post(
    "/experiments/{exp_id}/export",
    response_model=ExportPackageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Preflight error or insufficient storage"},
        404: {"model": ErrorResponse, "description": "Experiment or artifacts not found"},
        500: {"model": ErrorResponse, "description": "Internal export error"},
    },
)
def create_export(exp_id: str, create_zip: bool = Query(default=True)):
    """
    Creates a reproducible, self-contained export package for the specified experiment.
    Generates manifest.json, loader.py, and MODEL_CARD.md, and optionally zips the bundle.
    """
    try:
        res = export_service.create_export_package(exp_id=exp_id, create_zip=create_zip)
        return res
    except ExportPreflightError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get(
    "/experiments/{exp_id}/export",
    response_model=ExportPackageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Export package not found"},
    },
)
def get_export_manifest(exp_id: str):
    """
    Retrieves the export manifest and metadata for an existing exported experiment.
    """
    pkg_dir = settings.base_dir / "exports" / f"export_{exp_id}_int8"
    manifest_file = pkg_dir / "manifest.json"
    archive_file = settings.base_dir / "exports" / f"export_{exp_id}_int8.zip"

    if not manifest_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export manifest for experiment '{exp_id}' not found.",
        )

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    archive_size_mb = None
    archive_sha = None
    if archive_file.exists():
        archive_size_mb = round(archive_file.stat().st_size / (1024 * 1024), 2)
        archive_sha = compute_file_sha256(archive_file)

    files_count = len(manifest.get("files", [])) + 1

    return ExportPackageResponse(
        export_id=f"export_{exp_id}_int8",
        experiment_id=exp_id,
        package_directory=str(pkg_dir),
        archive_path=str(archive_file) if archive_file.exists() else None,
        archive_size_mb=archive_size_mb,
        archive_sha256=archive_sha,
        files_count=files_count,
        manifest=manifest,
    )


@router.post(
    "/exports/verify",
    response_model=ExportVerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Verification error or invalid target"},
        404: {"model": ErrorResponse, "description": "Export target not found"},
    },
)
def verify_export(payload: ExportVerifyRequest):
    """
    Verifies an export package (directory or .zip archive) against its manifest.json.
    Computes real-time SHA-256 digests and checks for missing or altered files.
    """
    target = None
    if payload.target_path:
        target = Path(payload.target_path)
    elif payload.export_id:
        # Check for zip first, then dir
        zip_path = settings.base_dir / "exports" / f"{payload.export_id}.zip"
        dir_path = settings.base_dir / "exports" / payload.export_id
        if zip_path.exists():
            target = zip_path
        elif dir_path.exists():
            target = dir_path

    if not target or not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification target not found on disk.",
        )

    try:
        return export_service.verify_package(target)
    except ExportVerificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        )
