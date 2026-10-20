"""
Pydantic v2 schemas for EcoCompress AI API.
Defines strict validation rules for requests, responses, and state models.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class TaskType(str, Enum):
    TEXT_CLASSIFICATION = "text-classification"
    TEXT_GENERATION = "text-generation"
    QUESTION_ANSWERING = "question-answering"


class OptimizationType(str, Enum):
    ONNX_DYNAMIC_INT8 = "onnx-dynamic-int8"
    TORCH_DYNAMIC_INT8 = "torch-dynamic-int8"
    TORCH_FP16 = "torch-fp16"
    BITSANDBYTES_4BIT = "bitsandbytes-4bit"


class ExperimentStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    VALIDATING = "validating"
    PROFILING = "profiling"
    BASELINE_RUNNING = "baseline_running"
    OPTIMIZING = "optimizing"
    CANDIDATE_RUNNING = "candidate_running"
    VALIDATING_CANDIDATE = "validating_candidate"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Allowed state transitions graph
VALID_TRANSITIONS: Dict[ExperimentStatus, List[ExperimentStatus]] = {
    ExperimentStatus.CREATED: [ExperimentStatus.QUEUED, ExperimentStatus.CANCELLED],
    ExperimentStatus.QUEUED: [ExperimentStatus.VALIDATING, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.VALIDATING: [ExperimentStatus.PROFILING, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.PROFILING: [ExperimentStatus.BASELINE_RUNNING, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.BASELINE_RUNNING: [ExperimentStatus.OPTIMIZING, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.OPTIMIZING: [ExperimentStatus.CANDIDATE_RUNNING, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.CANDIDATE_RUNNING: [ExperimentStatus.VALIDATING_CANDIDATE, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    ExperimentStatus.VALIDATING_CANDIDATE: [ExperimentStatus.COMPLETED, ExperimentStatus.CANCELLED, ExperimentStatus.FAILED],
    # Terminal states have NO outgoing transitions
    ExperimentStatus.COMPLETED: [],
    ExperimentStatus.FAILED: [],
    ExperimentStatus.CANCELLED: [],
}


class WorkloadConfig(BaseModel):
    task: TaskType = TaskType.TEXT_CLASSIFICATION
    dataset: str = Field(default="SST-2 Subset", min_length=2, max_length=200)
    sample_count: int = Field(default=500, ge=1, le=10000)
    batch_size: int = Field(default=1, ge=1, le=128)
    sequence_length: int = Field(default=128, ge=8, le=4096)
    warmup_runs: int = Field(default=10, ge=0, le=100)
    measured_runs: int = Field(default=50, ge=1, le=1000)


class AcceptanceThresholds(BaseModel):
    max_quality_loss_pct: float = Field(default=3.0, ge=0.0, le=100.0)
    min_size_reduction_pct: float = Field(default=40.0, ge=0.0, le=100.0)
    max_latency_increase_pct: float = Field(default=0.0, ge=-100.0, le=1000.0)


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    model_id: str = Field(..., min_length=2, max_length=150)
    task: TaskType = TaskType.TEXT_CLASSIFICATION
    optimization_method: OptimizationType = OptimizationType.ONNX_DYNAMIC_INT8
    workload_config: WorkloadConfig = Field(default_factory=WorkloadConfig)
    thresholds: AcceptanceThresholds = Field(default_factory=AcceptanceThresholds)

    @field_validator("model_id")
    @classmethod
    def validate_safe_model_id(cls, v: str) -> str:
        clean = v.strip()
        # Security rule: Reject path traversal and suspicious shell symbols
        if ".." in clean or clean.startswith("/") or clean.startswith("\\"):
            raise ValueError("Invalid model identifier: path traversal sequence detected.")
        if any(c in clean for c in [";", "&", "|", "`", "$", "<", ">", "\n", "\r"]):
            raise ValueError("Invalid model identifier: forbidden special characters.")
        return clean

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Experiment name cannot be empty.")
        return clean


class AcceptanceDecision(BaseModel):
    passed: bool
    reasons: List[str]
    timestamp: str


class BenchmarkMetric(BaseModel):
    value: Optional[float]
    unit: str
    type: str  # 'measured', 'estimated', 'unavailable'
    notes: Optional[str] = None


class BenchmarkSummary(BaseModel):
    artifact_size_mb: BenchmarkMetric
    median_latency_ms: BenchmarkMetric
    p95_latency_ms: BenchmarkMetric
    peak_memory_mb: BenchmarkMetric
    quality_score: BenchmarkMetric
    energy_joules: BenchmarkMetric
    carbon_grams: BenchmarkMetric
    water_milliliters: BenchmarkMetric


class ExperimentResponse(BaseModel):
    id: str
    name: str
    model_id: str
    task: TaskType
    optimization_method: OptimizationType
    workload_config: WorkloadConfig
    thresholds: AcceptanceThresholds
    status: ExperimentStatus
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_summary: Optional[str] = None
    acceptance_decision: Optional[AcceptanceDecision] = None
    baseline_metrics: Optional[BenchmarkSummary] = None
    candidate_metrics: Optional[BenchmarkSummary] = None


class ExperimentSummaryItem(BaseModel):
    id: str
    name: str
    model_id: str
    task: TaskType
    optimization_method: OptimizationType
    status: ExperimentStatus
    created_at: str
    updated_at: str
    passed: Optional[bool] = None


class ExperimentListResponse(BaseModel):
    total: int
    experiments: List[ExperimentSummaryItem]


class JobStatusResponse(BaseModel):
    id: str
    experiment_id: str
    status: ExperimentStatus
    current_step: str
    progress_pct: int
    created_at: str
    updated_at: str
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    phase: str
    service: str
    version: str


class StorageDrive(BaseModel):
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
    storage: Dict[str, StorageDrive]
    gpu_profile: Dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
    code: str
    hint: Optional[str] = None


class BenchmarkConfigSchema(BaseModel):
    warmup_runs: int = Field(default=5, ge=0, le=100)
    measured_runs: int = Field(default=20, ge=1, le=500)
    batch_size: int = Field(default=1, ge=1, le=64)
    sequence_length: int = Field(default=128, ge=8, le=4096)
    target_device: str = Field(default="cpu")
    random_seed: int = Field(default=42)
    timeout_seconds: float = Field(default=300.0, ge=1.0)
    collect_memory: bool = Field(default=True)


class LatencyDetailSchema(BaseModel):
    median_ms: float
    p95_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    sample_count: int
    raw_samples_ms: Optional[List[float]] = None


class MemoryDetailSchema(BaseModel):
    baseline_rss_mb: float
    peak_rss_mb: float
    peak_rss_delta_mb: float
    peak_gpu_mb: Optional[float] = None
    gpu_device_name: Optional[str] = None
    measurement_type: str = "measured"
    notes: Optional[str] = None


class BenchmarkDetailResponse(BaseModel):
    id: Optional[int] = None
    experiment_id: str
    candidate_type: str  # 'baseline' or 'candidate'
    model_id: str
    model_revision: Optional[str] = None
    artifact_size_mb: Optional[float] = None
    latency: LatencyDetailSchema
    memory: MemoryDetailSchema
    quality_score: Optional[float] = None
    quality_metric_name: Optional[str] = None
    energy_joules: Optional[float] = None
    energy_measurement_type: str = "unavailable"
    carbon_grams: Optional[float] = None
    carbon_measurement_type: str = "unavailable"
    water_milliliters: Optional[float] = None
    water_measurement_type: str = "unavailable"
    measured_runs: int
    warmup_runs: int
    hardware_device: str
    runtime_name: str
    workload_snapshot: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    recorded_at: str


class ExportPackageResponse(BaseModel):
    export_id: str
    experiment_id: str
    package_directory: str
    archive_path: Optional[str] = None
    archive_size_mb: Optional[float] = None
    archive_sha256: Optional[str] = None
    files_count: int
    manifest: Dict[str, Any]


class ExportVerifyRequest(BaseModel):
    target_path: Optional[str] = None
    export_id: Optional[str] = None


class ExportVerifyResponse(BaseModel):
    passed: bool
    verified_files_count: int
    total_expected_files: int
    verified_files: List[str]
    missing_files: List[str]
    mismatched_files: List[Dict[str, Any]]
    manifest: Optional[Dict[str, Any]] = None

