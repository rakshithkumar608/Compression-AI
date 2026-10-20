export type ModelTask = "text-classification" | "text-generation" | "question-answering";

export type OptimizationMethod = 
  | "onnx-dynamic-int8" 
  | "torch-dynamic-int8" 
  | "torch-fp16" 
  | "bitsandbytes-4bit";

export type JobStatus = 
  | "created"
  | "queued" 
  | "validating" 
  | "profiling" 
  | "baseline_running" 
  | "optimizing" 
  | "candidate_running" 
  | "validating_candidate" 
  | "completed" 
  | "failed" 
  | "cancelled";

export interface ModelProfile {
  id: string;
  name: string;
  task: ModelTask;
  parameters: string;
  sourceFormat: "safetensors" | "bin" | "onnx";
  estimatedVramMb: number;
  originalSizeMb: number;
  license: string;
  supportedOnDevice: boolean;
  notes: string;
}

export interface WorkloadConfig {
  task: ModelTask;
  dataset: string;
  sample_count: number;
  batch_size: number;
  sequence_length: number;
  warmup_runs: number;
  measured_runs: number;
}

export interface AcceptanceThresholds {
  max_quality_loss_pct: number;
  min_size_reduction_pct: number;
  max_latency_increase_pct: number;
}

export interface MetricValue {
  value: number | null;
  unit: string;
  type: "measured" | "estimated" | "unavailable";
  methodNotes?: string;
}

export interface BenchmarkMetrics {
  artifactSizeMb: MetricValue;
  medianLatencyMs: MetricValue;
  p95LatencyMs: MetricValue;
  peakMemoryMb: MetricValue;
  qualityScore: MetricValue;
  energyJoules: MetricValue;
  carbonGrams: MetricValue;
  waterMilliliters: MetricValue;
}

export interface AcceptanceDecision {
  passed: boolean;
  reasons: string[];
  timestamp: string;
}

export interface ExperimentRun {
  id: string;
  name: string;
  createdAt: string;
  status: JobStatus;
  isIllustrativeDemo: boolean;
  model: ModelProfile;
  workload: {
    task: ModelTask;
    dataset: string;
    sampleCount: number;
    batchSize: number;
    sequenceLength: number;
    warmupRuns: number;
    measuredRuns: number;
  };
  optimizationMethod: OptimizationMethod;
  thresholds: {
    maxQualityLossPct: number;
    minSizeReductionPct: number;
    maxLatencyIncreasePct: number;
  };
  baseline?: BenchmarkMetrics;
  candidate?: BenchmarkMetrics;
  acceptanceDecision?: AcceptanceDecision;
}

export interface ExperimentResponse {
  id: string;
  name: string;
  model_id: string;
  task: ModelTask;
  optimization_method: OptimizationMethod;
  workload_config: WorkloadConfig;
  thresholds: AcceptanceThresholds;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_summary?: string | null;
  acceptance_decision?: AcceptanceDecision | null;
}

export interface ExperimentSummaryItem {
  id: string;
  name: string;
  model_id: string;
  task: ModelTask;
  optimization_method: OptimizationMethod;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  passed?: boolean | null;
}

export interface ExperimentListResponse {
  total: number;
  experiments: ExperimentSummaryItem[];
}

export interface ExperimentCreate {
  name: string;
  model_id: string;
  task: ModelTask;
  optimization_method: OptimizationMethod;
  workload_config: WorkloadConfig;
  thresholds: AcceptanceThresholds;
}

export interface JobStatusResponse {
  id: string;
  experiment_id: string;
  status: JobStatus;
  current_step: string;
  progress_pct: number;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
}

export interface HealthResponse {
  status: string;
  phase: string;
  service: string;
  version: string;
}

export interface StorageDrive {
  drive: string;
  total_gb: number;
  free_gb: number;
  free_mb: number;
}

export interface SystemSummary {
  os: string;
  os_release: string;
  python_version: string;
  total_ram_gb: number;
  free_ram_gb: number;
  storage: Record<string, {
    drive: string;
    total_gb: number;
    free_gb: number;
    free_mb: number;
  }>;
  gpu_profile: {
    model: string;
    vram_mb: number;
    driver_version: string;
    cuda_support: string;
    concurrency_limit: number;
  };
}

export interface SystemHardware {
  os: string;
  ramTotalGb: number;
  ramFreeGb: number;
  gpuName: string;
  gpuVramMb: number;
  driverVersion: string;
  cudaVersion: string;
  cDriveFreeMb: number;
  dDriveFreeGb: number;
  pythonVersion: string;
  nodeVersion: string;
}
