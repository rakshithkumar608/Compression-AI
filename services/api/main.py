"""
EcoCompress AI - FastAPI Backend Service (Phase 2)
Decoupled API service for reproducible model compression evaluation.
Manages experiment metadata, validation, lifecycle states, and hardware diagnostics.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure services/api directory is in sys.path for modular imports
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings
from database import init_db
from routers import health, experiments, hardware, models
from schemas import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables safely on D: drive on startup
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evidence-based AI model compression evaluation API with SQLite persistence.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS restricted strictly to configured local frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(health.router)
app.include_router(experiments.router)
app.include_router(hardware.router)
app.include_router(models.router)


# Global Exception Handlers for Uniform Error Responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request body")
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    detail = f"{msg} at {loc}" if loc else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail=detail,
            code="VALIDATION_ERROR",
            hint="Check that all required fields meet the specified constraints.",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail=f"Internal service error: {str(exc)}",
            code="INTERNAL_SERVER_ERROR",
            hint="Inspect backend server logs for full stacktrace.",
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=True)
