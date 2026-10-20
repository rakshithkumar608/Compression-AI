"use client";

import React, { useState } from "react";
import {
  Box,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Cpu,
  Search,
  RefreshCw,
  AlertCircle,
  HelpCircle,
  HardDrive,
  Info,
} from "lucide-react";
import { SUPPORTED_MODEL_CATALOG, HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";
import { ModelProfile } from "@/types";
import { api, ApiError } from "@/lib/api";

interface ModelWorkspaceViewProps {
  onSelectModelForExperiment?: (model: ModelProfile) => void;
}

export const ModelWorkspaceView: React.FC<ModelWorkspaceViewProps> = ({
  onSelectModelForExperiment,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<ModelProfile>(SUPPORTED_MODEL_CATALOG[0]);
  const [inputModelId, setInputModelId] = useState("");
  const [inputSource, setInputSource] = useState<"huggingface" | "local">("huggingface");

  const [isLoading, setIsLoading] = useState(false);
  const [inspectedData, setInspectedData] = useState<any | null>(null);
  const [inspectionError, setInspectionError] = useState<string | null>(null);

  const handleInspect = async (modelIdToInspect: string, source: "huggingface" | "local" = "huggingface") => {
    if (!modelIdToInspect.trim()) return;

    setIsLoading(true);
    setInspectionError(null);

    try {
      const result = await api.inspectModel(modelIdToInspect, source, 1, 128);
      setInspectedData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setInspectionError(`[${err.code || "ERROR"}] ${err.message}`);
      } else {
        setInspectionError(err instanceof Error ? err.message : "Failed to inspect model. Check backend status.");
      }
      setInspectedData(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Inspect the default preset on first load if not inspected yet
  const activeMeta = inspectedData?.metadata;
  const activeFeasibility = inspectedData?.feasibility;

  const currentName = activeMeta?.name || selectedPreset.name;
  const currentId = activeMeta?.model_id || selectedPreset.id;
  const currentArch = activeMeta?.architecture || "Transformer";
  const currentTask = activeMeta?.task || selectedPreset.task;
  const currentParams = activeMeta?.parameter_count
    ? `${(activeMeta.parameter_count / 1_000_000).toFixed(1)}M`
    : selectedPreset.parameters;
  const currentFormat = activeMeta?.format || selectedPreset.sourceFormat;
  const currentLicense = activeMeta?.license || selectedPreset.license;

  const verdict = activeFeasibility?.verdict || "feasible";
  const verdictLabel = activeFeasibility?.verdict_label || "Hardware Feasible";
  const verdictReason = activeFeasibility?.reason || selectedPreset.notes;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Model Workspace & Safe Inspector</h2>
        <p className="text-xs text-slate-400 mt-1">
          Safely inspect model configurations, exact parameter counts, safetensors headers, and host VRAM feasibility without downloading weights.
        </p>
      </div>

      {/* Model Selection & Custom Search Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Preset Catalog & Live Query Form */}
        <div className="space-y-4">
          {/* Preset Buttons */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Supported Model Presets
            </h3>
            <div className="space-y-2">
              {SUPPORTED_MODEL_CATALOG.map((m) => {
                const isSelected = selectedPreset.id === m.id && !inputModelId;
                return (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedPreset(m);
                      setInputModelId("");
                      handleInspect(m.id, "huggingface");
                    }}
                    className={`w-full text-left p-3 rounded-lg border text-xs transition ${
                      isSelected
                        ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                        : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <div className="font-semibold text-slate-200">{m.name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5 flex justify-between">
                      <span>{m.task}</span>
                      <span className="font-mono">{m.parameters}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Inspect Arbitrary Repository or Local Path */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Inspect External Reference
            </h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleInspect(inputModelId, inputSource);
              }}
              className="space-y-3"
            >
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Source Type</label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setInputSource("huggingface")}
                    className={`py-1.5 rounded-lg border font-medium ${
                      inputSource === "huggingface"
                        ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    Hugging Face Hub
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputSource("local")}
                    className={`py-1.5 rounded-lg border font-medium ${
                      inputSource === "local"
                        ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}
                  >
                    Local Directory
                  </button>
                </div>
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1">
                  {inputSource === "huggingface" ? "Hugging Face Model ID" : "Approved Local Path (in artifacts/)"}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={inputModelId}
                    onChange={(e) => setInputModelId(e.target.value)}
                    placeholder={inputSource === "huggingface" ? "e.g. roberta-base or Qwen/Qwen2.5-0.5B" : "D:/Projects/Compression AI/artifacts/my-model"}
                    className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                  <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Inspecting Safely...
                  </>
                ) : (
                  <>
                    <Search className="h-3.5 w-3.5" />
                    Inspect Metadata (Read-Only)
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Detailed Inspection & Resource Feasibility Card */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <Box className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-lg font-bold text-white">{currentName}</h3>
                </div>
                <p className="text-xs font-mono text-slate-400 mt-0.5">{currentId}</p>
              </div>

              {/* Feasibility Verdict Badge */}
              <div>
                {verdict === "feasible" && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                    <CheckCircle2 className="h-3.5 w-3.5" /> {verdictLabel}
                  </span>
                )}
                {verdict === "tight" && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5" /> {verdictLabel}
                  </span>
                )}
                {verdict === "exceeds_vram" && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold">
                    <AlertCircle className="h-3.5 w-3.5" /> {verdictLabel}
                  </span>
                )}
                {verdict === "cannot_determine" && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-xs font-semibold">
                    <HelpCircle className="h-3.5 w-3.5" /> {verdictLabel}
                  </span>
                )}
              </div>
            </div>

            {/* Error Message if inspection failed */}
            {inspectionError && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300 flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">Inspection Blocked / Error:</div>
                  <div className="mt-0.5">{inspectionError}</div>
                </div>
              </div>
            )}

            {/* Security Warnings if any */}
            {activeMeta?.security_warnings?.map((warn: string, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                <span>{warn}</span>
              </div>
            ))}

            {/* Specification Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Architecture</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block truncate">
                  {currentArch}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Parameter Count</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block font-mono">
                  {currentParams}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Weight Checkpoint Format</span>
                <span className="text-xs font-semibold text-emerald-400 mt-1 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3" /> {currentFormat}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Task Category</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block uppercase">
                  {currentTask}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Declared License</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">
                  {currentLicense}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Disk Weight Size</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block font-mono">
                  {activeMeta?.total_weight_size_mb ? `~${activeMeta.total_weight_size_mb} MB` : `~${selectedPreset.originalSizeMb} MB`}
                </span>
              </div>
            </div>

            {/* Feasibility Memory Breakdown by Precision */}
            {activeFeasibility?.memory_estimates && (
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-blue-400" />
                  Estimated Memory by Precision Option
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">FP32 (Original)</span>
                    <span className="font-mono font-bold text-slate-200 mt-0.5 block">
                      {activeFeasibility.memory_estimates.fp32_mb} MB
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">FP16 / BF16</span>
                    <span className="font-mono font-bold text-slate-200 mt-0.5 block">
                      {activeFeasibility.memory_estimates.fp16_mb} MB
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                    <span className="text-[10px] text-emerald-400 block font-medium">INT8 Quantized</span>
                    <span className="font-mono font-bold text-emerald-300 mt-0.5 block">
                      {activeFeasibility.memory_estimates.int8_quantized_mb} MB
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">INT4 (4-bit)</span>
                    <span className="font-mono font-bold text-purple-300 mt-0.5 block">
                      {activeFeasibility.memory_estimates.int4_quantized_mb} MB
                    </span>
                  </div>
                </div>

                {/* VRAM Headroom Meter */}
                <div className="pt-2 space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300">
                      Total Footprint (INT8 + Activations) vs RTX 2050 (4,096 MB)
                    </span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {activeFeasibility.memory_estimates.total_estimated_int8_mb} MB / 4096 MB
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        verdict === "exceeds_vram" ? "bg-red-500" : verdict === "tight" ? "bg-amber-500" : "bg-emerald-500"
                      }`}
                      style={{
                        width: `${Math.min(
                          100,
                          Math.round((activeFeasibility.memory_estimates.total_estimated_int8_mb / 4096) * 100)
                        )}%`,
                      }}
                    ></div>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {verdictReason}
                  </p>
                </div>
              </div>
            )}

            {/* Assumptions & Uncertainty Disclaimer */}
            {activeFeasibility?.assumptions && (
              <div className="p-3.5 rounded-xl bg-slate-800/30 border border-slate-800 space-y-1.5 text-[11px] text-slate-400">
                <span className="font-semibold text-slate-300 block">Calculation Assumptions & Uncertainty:</span>
                <ul className="list-disc pl-4 space-y-0.5">
                  {activeFeasibility.assumptions.map((ass: string, i: number) => (
                    <li key={i}>{ass}</li>
                  ))}
                </ul>
                <p className="text-amber-300/80 pt-1">
                  {activeFeasibility.uncertainty_disclaimer}
                </p>
              </div>
            )}

            {/* Action */}
            <div className="pt-2 flex justify-end">
              {onSelectModelForExperiment && verdict === "feasible" && (
                <button
                  onClick={() =>
                    onSelectModelForExperiment({
                      id: currentId,
                      name: currentName,
                      task: currentTask,
                      parameters: currentParams,
                      sourceFormat: currentFormat,
                      estimatedVramMb: activeFeasibility?.memory_estimates?.total_estimated_int8_mb || 600,
                      originalSizeMb: activeMeta?.total_weight_size_mb || selectedPreset.originalSizeMb,
                      license: currentLicense,
                      supportedOnDevice: true,
                      notes: verdictReason,
                    })
                  }
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                >
                  Use for New Experiment
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
