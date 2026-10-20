export type ModelTask = "text-classification" | "text-generation" | "question-answering";

export type OptimizationMethod = 
  | "onnx-dynamic-int8" 
  | "torch-dynamic-int8" 
  | "torch-fp16" 
  | "bitsandbytes-4bit";

export type JobStatus = 
  | "idle" 
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
  sampleCount: number;
  batchSize: number;
  sequenceLength: number;
  warmupRuns: number;
  measuredRuns: number;
}

export interface AcceptanceThresholds {
  maxQualityLossPct: number;
  minSizeReductionPct: number;
  maxLatencyIncreasePct: number;
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
  qualityScore: MetricValue; // e.g. Accuracy or Perplexity
  energyJoules: MetricValue;
  carbonGrams: MetricValue;
  waterMilliliters: MetricValue;
}

export interface ExperimentRun {
  id: string;
  name: string;
  createdAt: string;
  status: JobStatus;
  isIllustrativeDemo: boolean;
  model: ModelProfile;
  workload: WorkloadConfig;
  optimizationMethod: OptimizationMethod;
  thresholds: AcceptanceThresholds;
  baseline?: BenchmarkMetrics;
  candidate?: BenchmarkMetrics;
  acceptanceDecision?: {
    passed: boolean;
    reasons: string[];
    timestamp: string;
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
