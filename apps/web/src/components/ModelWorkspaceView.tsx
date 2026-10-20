"use client";

import React, { useState } from "react";
import { Box, CheckCircle2, AlertTriangle, ShieldCheck, HardDrive, Cpu, Search } from "lucide-react";
import { SUPPORTED_MODEL_CATALOG, HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";
import { ModelProfile } from "@/types";

interface ModelWorkspaceViewProps {
  onSelectModelForExperiment?: (model: ModelProfile) => void;
}

export const ModelWorkspaceView: React.FC<ModelWorkspaceViewProps> = ({
  onSelectModelForExperiment,
}) => {
  const [selectedModel, setSelectedModel] = useState<ModelProfile>(SUPPORTED_MODEL_CATALOG[0]);
  const [customModelId, setCustomModelId] = useState("");
  const [formatWarning, setFormatWarning] = useState<string | null>(null);

  const handleCustomModelInspect = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customModelId.trim()) return;

    // Simulate inspection check complying with security rules
    if (customModelId.toLowerCase().includes("7b") || customModelId.toLowerCase().includes("8b")) {
      setSelectedModel({
        id: customModelId,
        name: `Custom Model: ${customModelId}`,
        task: "text-generation",
        parameters: "~7B",
        sourceFormat: "safetensors",
        estimatedVramMb: 14500,
        originalSizeMb: 14000,
        license: "Unknown / Untrusted",
        supportedOnDevice: false,
        notes: "Exceeds host 4GB VRAM limit. Will trigger CUDA OOM or heavy swap paging.",
      });
      setFormatWarning("High Memory Warning: Model size (~14GB) exceeds the 4GB VRAM available on your RTX 2050.");
    } else {
      setSelectedModel({
        id: customModelId,
        name: `Custom Model: ${customModelId}`,
        task: "text-classification",
        parameters: "~100M",
        sourceFormat: "safetensors",
        estimatedVramMb: 800,
        originalSizeMb: 350,
        license: "Requires verification",
        supportedOnDevice: true,
        notes: "Model fits within 4GB VRAM envelope. Ready for baseline benchmark profiling.",
      });
      setFormatWarning(null);
    }
  };

  const vramUsagePct = Math.min(100, Math.round((selectedModel.estimatedVramMb / HOST_SYSTEM_DIAGNOSTICS.gpuVramMb) * 100));
  const isVramFeasible = selectedModel.estimatedVramMb <= HOST_SYSTEM_DIAGNOSTICS.gpuVramMb;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Model Workspace & Safe Inspector</h2>
        <p className="text-xs text-slate-400 mt-1">
          Inspect model architectures, format safety, license status, and host VRAM compatibility before queuing any workloads.
        </p>
      </div>

      {/* Model Selection & Custom Search Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Preset Catalog & Inspector Input */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Supported Model Presets
            </h3>
            <div className="space-y-2">
              {SUPPORTED_MODEL_CATALOG.map((m) => {
                const isSelected = selectedModel.id === m.id;
                return (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedModel(m);
                      setFormatWarning(null);
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

          {/* Inspect Custom Model Reference */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Inspect External Reference
            </h3>
            <form onSubmit={handleCustomModelInspect} className="space-y-3">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">
                  Hugging Face ID or Local Path
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={customModelId}
                    onChange={(e) => setCustomModelId(e.target.value)}
                    placeholder="e.g. roberta-base"
                    className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                  <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                </div>
              </div>
              <button
                type="submit"
                className="w-full py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition"
              >
                Inspect Metadata (Read-Only)
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Detailed Model Inspection Card */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <Box className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-lg font-bold text-white">{selectedModel.name}</h3>
                </div>
                <p className="text-xs font-mono text-slate-400 mt-0.5">{selectedModel.id}</p>
              </div>

              {/* Compatibility Badge */}
              <div>
                {isVramFeasible ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Hardware Compatible
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5" /> Exceeds 4GB VRAM
                  </span>
                )}
              </div>
            </div>

            {/* Warning if any */}
            {formatWarning && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{formatWarning}</span>
              </div>
            )}

            {/* Specification Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Task Category</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block uppercase">
                  {selectedModel.task}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Parameter Count</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block font-mono">
                  {selectedModel.parameters}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Weight Format</span>
                <span className="text-xs font-semibold text-emerald-400 mt-1 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3" /> {selectedModel.sourceFormat}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Original Disk Size</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">
                  ~{selectedModel.originalSizeMb} MB
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">Est. Runtime VRAM</span>
                <span className={`text-xs font-semibold mt-1 block ${isVramFeasible ? "text-slate-200" : "text-red-400"}`}>
                  ~{selectedModel.estimatedVramMb} MB
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-[11px] text-slate-400 block">License</span>
                <span className="text-xs font-semibold text-slate-200 mt-1 block">
                  {selectedModel.license}
                </span>
              </div>
            </div>

            {/* VRAM Utilization Meter */}
            <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300 font-medium flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-blue-400" />
                  Estimated VRAM Footprint vs RTX 2050 (4,096 MB)
                </span>
                <span className="font-mono text-slate-400">
                  {selectedModel.estimatedVramMb} MB / 4096 MB ({vramUsagePct}%)
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    vramUsagePct > 90 ? "bg-red-500" : vramUsagePct > 60 ? "bg-amber-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(100, vramUsagePct)}%` }}
                ></div>
              </div>
              <p className="text-[11px] text-slate-400">
                Safety margin: Recommended maximum model VRAM footprint is 2,500 MB to prevent display driver reset.
              </p>
            </div>

            {/* Notes & Actions */}
            <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <p className="text-xs text-slate-400 max-w-md">
                {selectedModel.notes}
              </p>
              {onSelectModelForExperiment && isVramFeasible && (
                <button
                  onClick={() => onSelectModelForExperiment(selectedModel)}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shrink-0"
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
