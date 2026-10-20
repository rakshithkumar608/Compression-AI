"use client";

import React, { useState } from "react";
import { Play, ShieldCheck, AlertCircle, CheckCircle2, Sliders, HardDrive, Cpu, RefreshCw } from "lucide-react";
import { SUPPORTED_MODEL_CATALOG, HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";
import { JobStatus, ModelProfile, OptimizationMethod } from "@/types";

interface ExperimentSetupViewProps {
  initialModel?: ModelProfile;
  onExperimentComplete?: () => void;
}

export const ExperimentSetupView: React.FC<ExperimentSetupViewProps> = ({
  initialModel = SUPPORTED_MODEL_CATALOG[0],
}) => {
  const [selectedModel, setSelectedModel] = useState<ModelProfile>(initialModel);
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

  const [jobState, setJobState] = useState<JobStatus>("idle");
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  const pipelineSteps: { status: JobStatus; label: string }[] = [
    { status: "queued", label: "Job Queued in SQLite" },
    { status: "validating", label: "Validating Runtime & D: Storage" },
    { status: "profiling", label: "Profiling Model Architecture" },
    { status: "baseline_running", label: "Evaluating Baseline Workload" },
    { status: "optimizing", label: "Executing Quantization Pipeline" },
    { status: "candidate_running", label: "Evaluating Candidate Workload" },
    { status: "validating_candidate", label: "Applying Acceptance Gate" },
    { status: "completed", label: "Report Provenance Stored" },
  ];

  const handleStartSimulation = () => {
    if (jobState !== "idle" && jobState !== "completed" && jobState !== "failed") return;

    setJobState("queued");
    setActiveStepIndex(0);

    let current = 0;
    const interval = setInterval(() => {
      current++;
      if (current < pipelineSteps.length) {
        setActiveStepIndex(current);
        setJobState(pipelineSteps[current].status);
      } else {
        clearInterval(interval);
        setJobState("completed");
      }
    }, 1200);
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: The Setup Form */}
        <div className="lg:col-span-2 space-y-6">
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
                    onClick={() => setSelectedModel(m)}
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
                  <HardDrive className="h-3.5 w-3.5 text-emerald-400" />
                  Target Artifact Disk:
                </span>
                <span className="font-semibold text-emerald-400">D: Drive ({HOST_SYSTEM_DIAGNOSTICS.dDriveFreeGb} GB)</span>
              </div>

              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
                  C: Drive Write Protection:
                </span>
                <span className="font-semibold text-amber-400">Guarded (0 MB)</span>
              </div>

              <div className="flex items-center justify-between text-slate-300">
                <span className="flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-blue-400" />
                  Target Device:
                </span>
                <span className="font-semibold text-blue-400">RTX 2050 (4 GB)</span>
              </div>
            </div>

            <button
              onClick={handleStartSimulation}
              disabled={jobState !== "idle" && jobState !== "completed" && jobState !== "failed"}
              className={`w-full py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow transition ${
                jobState === "idle" || jobState === "completed" || jobState === "failed"
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer"
                  : "bg-slate-800 text-slate-400 cursor-not-allowed"
              }`}
            >
              {jobState === "idle" || jobState === "completed" || jobState === "failed" ? (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  Queue Benchmark Job
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Executing Pipeline Steps...
                </>
              )}
            </button>

            <p className="text-[11px] text-slate-400 text-center">
              Phase 1 interactive prototype. Real ML execution workers will connect in Phase 4-5.
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
                const isCurrent = idx === activeStepIndex && jobState !== "idle";
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
      </div>
    </div>
  );
};
