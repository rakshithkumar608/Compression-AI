"""
Experiment management endpoints for EcoCompress AI API.
Implements experiment creation, listing, retrieval, execution queuing, and cancellation.
"""

from fastapi import APIRouter, HTTPException, Query, status
from schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentListResponse,
    JobStatusResponse,
    ErrorResponse,
)
from services.experiment_service import (
    ExperimentService,
    ExperimentNotFoundError,
    InvalidStateTransitionError,
)

router = APIRouter(prefix="/experiments", tags=["Experiments"])
service = ExperimentService()


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error or unsafe input"},
    },
)
def create_experiment(payload: ExperimentCreate):
    """
    Creates a new experiment record in the SQLite database.
    Validates model ID for safety and initial state as 'created'.
    """
    try:
        return service.create_experiment(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create experiment: {str(e)}",
        )


@router.get("", response_model=ExperimentListResponse)
def list_experiments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Retrieves paginated experiment summaries ordered by creation date."""
    return service.list_experiments(limit=limit, offset=offset)


@router.get(
    "/{exp_id}",
    response_model=ExperimentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Experiment not found"},
    },
)
def get_experiment(exp_id: str):
    """Retrieves full experiment configuration, status, and benchmark outcomes by ID."""
    try:
        return service.get_experiment(exp_id)
    except ExperimentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{exp_id}' was not found in the database.",
        )


@router.post(
    "/{exp_id}/run",
    response_model=JobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"model": ErrorResponse, "description": "Experiment not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
)
def run_experiment(exp_id: str):
    """
    Enqueues an experiment into the decoupled background execution queue.
    Transitions experiment status from 'created' to 'queued'.
    """
    try:
        return service.enqueue_job(exp_id)
    except ExperimentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{exp_id}' was not found in the database.",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/{exp_id}/cancel",
    response_model=ExperimentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Experiment not found"},
        409: {"model": ErrorResponse, "description": "Experiment is in a non-cancellable terminal state"},
    },
)
def cancel_experiment(exp_id: str):
    """
    Cancels an active experiment.
    Cannot cancel an experiment that has already completed, failed, or been cancelled.
    """
    try:
        return service.cancel_experiment(exp_id)
    except ExperimentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{exp_id}' was not found in the database.",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
