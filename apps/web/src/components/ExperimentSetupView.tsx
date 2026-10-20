"use client";

import React, { useState } from "react";
import { Play, ShieldCheck, CheckCircle2, RefreshCw, AlertCircle, ArrowRight } from "lucide-react";
import { SUPPORTED_MODEL_CATALOG, HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";
import { JobStatus, ModelProfile, OptimizationMethod } from "@/types";
import { api } from "@/lib/api";

interface ExperimentSetupViewProps {
  initialModel?: ModelProfile;
  onExperimentComplete?: () => void;
}

export const ExperimentSetupView: React.FC<ExperimentSetupViewProps> = ({
  initialModel = SUPPORTED_MODEL_CATALOG[0],
  onExperimentComplete,
}) => {
  const [selectedModel, setSelectedModel] = useState<ModelProfile>(initialModel);
  const [experimentName, setExperimentName] = useState("DistilBERT SST-2 Compression Benchmark");
  const [dataset, setDataset] = useState("SST-2 (Stanford Sentiment Treebank) Subset");
  const [sampleCount, setSampleCount] = useState(500);
  const [batchSize, setBatchSize] = useState(1);
  const [seqLength, setSeqLength] = useState(128);
  const [warmupRuns, setWarmupRuns] = useState(10);
  const [measuredRuns, setMeasuredRuns] = useState(50);

  const [optimizationMethod, setOptimizationMethod] = useState<OptimizationMethod>("onnx-dynamic-int8");
  const [maxQualityLoss, setMaxQualityLoss] = useState(3.0);
  const [minSizeReduction, setMinSizeReduction] = useState(40.0);
  const [maxLatencyIncrease, setMaxLatencyIncrease] = useState(0.0);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdExpId, setCreatedExpId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const [jobState, setJobState] = useState<JobStatus>("created");
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  const pipelineSteps: { status: JobStatus; label: string }[] = [
    { status: "created", label: "Experiment Record Created" },
    { status: "queued", label: "Job Enqueued in SQLite" },
    { status: "validating", label: "Validating Runtime & D: Storage" },
    { status: "profiling", label: "Profiling Model Architecture" },
    { status: "baseline_running", label: "Evaluating Baseline Workload" },
    { status: "optimizing", label: "Executing Quantization Pipeline" },
    { status: "candidate_running", label: "Evaluating Candidate Workload" },
    { status: "validating_candidate", label: "Applying Acceptance Gate" },
    { status: "completed", label: "Report Provenance Stored" },
  ];

  const handleQueueExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      // 1. Send POST /experiments to live FastAPI backend
      const exp = await api.createExperiment({
        name: experimentName,
        model_id: selectedModel.id,
        task: selectedModel.task,
        optimization_method: optimizationMethod,
        workload_config: {
          task: selectedModel.task,
          dataset,
          sample_count: sampleCount,
          batch_size: batchSize,
          sequence_length: seqLength,
          warmup_runs: warmupRuns,
          measured_runs: measuredRuns,
        },
        thresholds: {
          max_quality_loss_pct: maxQualityLoss,
          min_size_reduction_pct: minSizeReduction,
          max_latency_increase_pct: maxLatencyIncrease,
        },
      });

      setCreatedExpId(exp.id);

      // 2. Enqueue the experiment job via POST /experiments/{id}/run
      const job = await api.runExperiment(exp.id);
      setJobState(job.status);
      setActiveStepIndex(1); // queued

      setSubmitSuccess(`Experiment ${exp.id} successfully persisted in SQLite and enqueued!`);
    } catch (err) {
      // Fallback: If backend is offline, simulate locally with notification
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Backend offline. Make sure 'python services/api/main.py' is running."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Experiment Setup & Benchmark Configuration</h2>
        <p className="text-xs text-slate-400 mt-1">
          Define reproducible benchmark conditions. Workloads and metrics will be saved in SQLite (`data/ecocompress.db`).
        </p>
      </div>

      {submitSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          <div className="flex-1 font-medium">{submitSuccess}</div>
          {onExperimentComplete && (
            <button
              onClick={onExperimentComplete}
              className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1 transition"
            >
              View in Dashboard <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {submitError && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-xs text-amber-300">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <div>
            <div className="font-semibold">Backend Connection Note:</div>
            <div className="mt-0.5">{submitError}</div>
          </div>
        </div>
      )}

      <form onSubmit={handleQueueExperiment} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: The Setup Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Experiment Name */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-2">
            <label className="text-xs font-semibold text-white block">Experiment Title</label>
            <input
              type="text"
              value={experimentName}
              onChange={(e) => setExperimentName(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Step 1: Model Selection */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">1</span>
              <span>Select Baseline Model</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {SUPPORTED_MODEL_CATALOG.map((m) => {
                const isSelected = selectedModel.id === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setSelectedModel(m);
                      setExperimentName(`${m.name} INT8 Benchmark`);
                    }}
                    className={`p-3 rounded-xl border text-left transition ${
                      isSelected
                        ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                        : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <div className="font-semibold text-xs text-slate-200">{m.name}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{m.task}</div>
                    <div className="text-[11px] font-mono text-emerald-400 mt-0.5">~{m.originalSizeMb} MB</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step 2: Workload & Evaluation Parameters */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">2</span>
              <span>Benchmark Workload Specification</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Fixed Task Dataset</label>
                <input
                  type="text"
                  value={dataset}
                  onChange={(e) => setDataset(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Evaluation Samples Count</label>
                <input
                  type="number"
                  value={sampleCount}
                  onChange={(e) => setSampleCount(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Batch Size</label>
                <input
                  type="number"
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Max Sequence Length (tokens)</label>
                <input
                  type="number"
                  value={seqLength}
                  onChange={(e) => setSeqLength(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Warm-up Runs (Discarded from Latency)</label>
                <input
                  type="number"
                  value={warmupRuns}
                  onChange={(e) => setWarmupRuns(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Measured Timing Runs</label>
                <input
                  type="number"
                  value={measuredRuns}
                  onChange={(e) => setMeasuredRuns(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
          </div>

          {/* Step 3: Quantization Pipeline Selection */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">3</span>
              <span>Optimization Method</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setOptimizationMethod("onnx-dynamic-int8")}
                className={`p-3 rounded-xl border text-left transition ${
                  optimizationMethod === "onnx-dynamic-int8"
                    ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                    : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <div className="font-semibold text-xs text-slate-200">ONNX Dynamic INT8</div>
                <div className="text-[11px] text-slate-400 mt-1">Recommended for Windows</div>
                <div className="text-[11px] text-emerald-400 mt-0.5">High Stability</div>
              </button>

              <button
                type="button"
                onClick={() => setOptimizationMethod("torch-dynamic-int8")}
                className={`p-3 rounded-xl border text-left transition ${
                  optimizationMethod === "torch-dynamic-int8"
                    ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                    : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <div className="font-semibold text-xs text-slate-200">PyTorch Dynamic INT8</div>
                <div className="text-[11px] text-slate-400 mt-1">torch.ao.quantization</div>
                <div className="text-[11px] text-blue-400 mt-0.5">Native CPU Kernels</div>
              </button>

              <button
                type="button"
                onClick={() => setOptimizationMethod("torch-fp16")}
                className={`p-3 rounded-xl border text-left transition ${
                  optimizationMethod === "torch-fp16"
                    ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                    : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                }`}
              >
                <div className="font-semibold text-xs text-slate-200">Half Precision (FP16)</div>
                <div className="text-[11px] text-slate-400 mt-1">CUDA Half Tensors</div>
                <div className="text-[11px] text-purple-400 mt-0.5">50% Storage Cut</div>
              </button>
            </div>
          </div>

          {/* Step 4: Acceptance Threshold Gating */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">4</span>
              <span>Acceptance Gate Thresholds</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <label className="text-slate-400 block mb-1">Max Allowable Quality Loss</label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step="0.1"
                    value={maxQualityLoss}
                    onChange={(e) => setMaxQualityLoss(Number(e.target.value))}
                    className="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white font-mono text-xs"
                  />
                  <span className="text-slate-400">%</span>
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">Default: 3.0%</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <label className="text-slate-400 block mb-1">Min Required Size Cut</label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step="1"
                    value={minSizeReduction}
                    onChange={(e) => setMinSizeReduction(Number(e.target.value))}
                    className="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white font-mono text-xs"
                  />
                  <span className="text-slate-400">%</span>
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">Default: 40.0%</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <label className="text-slate-400 block mb-1">Max Latency Degradation</label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step="0.5"
                    value={maxLatencyIncrease}
                    onChange={(e) => setMaxLatencyIncrease(Number(e.target.value))}
                    className="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white font-mono text-xs"
                  />
                  <span className="text-slate-400">%</span>
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">Default: 0.0% (no slowdown)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Dispatch & Lifecycle Monitor */}
        <div className="space-y-4">
          {/* Dispatch Action Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Execution Safety Pre-Flight</h3>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Target Database:
                </span>
                <span className="font-mono text-emerald-400">data/ecocompress.db</span>
              </div>

              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
                  C: Write Guard:
                </span>
                <span className="font-semibold text-amber-400">Guarded (0 MB)</span>
              </div>

              <div className="flex items-center justify-between text-slate-300">
                <span>Model Target:</span>
                <span className="font-semibold text-blue-400">{selectedModel.id}</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow transition bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer disabled:bg-slate-800 disabled:text-slate-400"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Saving to SQLite...
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  Queue Benchmark Job
                </>
              )}
            </button>

            {createdExpId && (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-300">
                <strong>Experiment ID:</strong> <span className="font-mono">{createdExpId}</span>
              </div>
            )}

            <p className="text-[11px] text-slate-400 text-center">
              Phase 2: Persists parameters and enqueues job state in SQLite. Real ML workers connect in Phase 4-5.
            </p>
          </div>

          {/* Job State Lifecycle Tracker */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Worker Lifecycle State Machine
            </h4>
            <div className="space-y-2 text-xs">
              {pipelineSteps.map((step, idx) => {
                const isPassed = idx < activeStepIndex;
                const isCurrent = idx === activeStepIndex;
                return (
                  <div
                    key={step.status}
                    className={`flex items-center gap-2.5 p-2 rounded-lg transition ${
                      isCurrent
                        ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-semibold"
                        : isPassed
                        ? "text-slate-300"
                        : "text-slate-400 opacity-60"
                    }`}
                  >
                    {isPassed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    ) : isCurrent ? (
                      <RefreshCw className="h-4 w-4 text-emerald-400 animate-spin shrink-0" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                    )}
                    <span>{step.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
