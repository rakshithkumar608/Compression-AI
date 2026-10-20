"use client";

import React, { useEffect, useState } from "react";
import { Cpu, HardDrive, Play, ArrowRight, AlertTriangle, Layers, CheckCircle2, Clock, RefreshCw, XCircle, AlertCircle } from "lucide-react";
import { HOST_SYSTEM_DIAGNOSTICS, ILLUSTRATIVE_DEMO_EXPERIMENT } from "@/lib/illustrativeData";
import { NavTab } from "./Sidebar";
import { api, ApiError } from "@/lib/api";
import { ExperimentSummaryItem } from "@/types";

interface DashboardViewProps {
  isIllustrativeActive: boolean;
  setIsIllustrativeActive: (val: boolean) => void;
  setActiveTab: (tab: NavTab) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  isIllustrativeActive,
  setIsIllustrativeActive,
  setActiveTab,
}) => {
  const [experiments, setExperiments] = useState<ExperimentSummaryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchRealExperiments = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.listExperiments(50, 0);
      setExperiments(data.experiments);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(`Backend API error (${err.status}): ${err.message}`);
      } else {
        setErrorMsg("Backend offline. Run 'python services/api/main.py' to enable live database persistence.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRealExperiments();
  }, []);

  const handleCancel = async (id: string) => {
    setActionInProgress(id);
    try {
      await api.cancelExperiment(id);
      await fetchRealExperiments();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to cancel experiment");
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Illustrative Preview Notice Banner */}
      {isIllustrativeActive && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <h4 className="font-semibold text-amber-300">
              Illustrative Preview Mode Active
            </h4>
            <p className="text-amber-200/80 text-xs mt-0.5">
              The benchmark data shown below is an illustrative UI schema preview to demonstrate visualization and acceptance gating.
              <strong> In accordance with EcoCompress AI product principles, no real models have been executed or metrics invented.</strong>
            </p>
          </div>
        </div>
      )}

      {/* Top Banner & Introduction */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-[#121c30] border border-slate-800">
        <div className="max-w-3xl">
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Evidence-Based AI Compression Workbench
          </h2>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            EcoCompress AI evaluates whether an optimized model retains task quality while reducing memory, latency, and energy footprint.
            Experiments and lifecycle states are persisted in SQLite (`data/ecocompress.db`) with decoupled background execution.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveTab("setup")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow transition"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              Configure New Experiment
            </button>
            <button
              onClick={() => setActiveTab("models")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold transition"
            >
              <Layers className="h-3.5 w-3.5" />
              Inspect Model Catalog
            </button>
          </div>
        </div>
      </div>

      {/* System Resource Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* GPU VRAM */}
        <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">GPU VRAM</span>
            <Cpu className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-white">
            {HOST_SYSTEM_DIAGNOSTICS.gpuVramMb / 1024} GB
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            {HOST_SYSTEM_DIAGNOSTICS.gpuName}
          </p>
          <div className="mt-3 text-[11px] text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> Driver 610.78 / CUDA 13.3
          </div>
        </div>

        {/* System Memory */}
        <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Host Memory (RAM)</span>
            <Layers className="h-4 w-4 text-purple-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-white">
            {HOST_SYSTEM_DIAGNOSTICS.ramTotalGb} GB
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            {HOST_SYSTEM_DIAGNOSTICS.ramFreeGb} GB free physical
          </p>
          <div className="mt-3 text-[11px] text-slate-400">
            Single-job concurrency enforced
          </div>
        </div>

        {/* D: Primary Storage */}
        <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">D: Storage (Artifacts & DB)</span>
            <HardDrive className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-emerald-400">
            {HOST_SYSTEM_DIAGNOSTICS.dDriveFreeGb} GB
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Healthy free storage on primary drive
          </p>
          <div className="mt-3 text-[11px] text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> ecocompress.db + artifacts on D:
          </div>
        </div>

        {/* C: Drive Protection Status */}
        <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">C: Drive Protection</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-amber-400">
            {HOST_SYSTEM_DIAGNOSTICS.cDriveFreeMb} MB
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Critical low free space guard
          </p>
          <div className="mt-3 text-[11px] text-amber-300/80">
            Zero package writes allowed on C:
          </div>
        </div>
      </div>

      {/* Experiments Section */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-lg font-semibold text-white">Experiments & Benchmark Runs</h3>
            <p className="text-xs text-slate-400">
              Live SQLite database persistence (`data/ecocompress.db`)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchRealExperiments}
              className="text-xs p-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              title="Refresh Experiments"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            {!isIllustrativeActive ? (
              <button
                onClick={() => setIsIllustrativeActive(true)}
                className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Load Illustrative Preview
              </button>
            ) : (
              <button
                onClick={() => setIsIllustrativeActive(false)}
                className="text-xs px-3 py-1.5 rounded-lg border border-amber-600/50 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 transition"
              >
                Switch to Clean Workspace
              </button>
            )}
          </div>
        </div>

        {/* Backend Warning Banner if Offline */}
        {errorMsg && (
          <div className="mt-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs text-amber-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Main View Area */}
        {isLoading ? (
          <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
            <RefreshCw className="h-5 w-5 animate-spin text-emerald-400" />
            <span>Querying SQLite database...</span>
          </div>
        ) : isIllustrativeActive ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-3 px-3">Experiment</th>
                  <th className="py-3 px-3">Task & Workload</th>
                  <th className="py-3 px-3">Method</th>
                  <th className="py-3 px-3">Size Reduction</th>
                  <th className="py-3 px-3">Latency Change</th>
                  <th className="py-3 px-3">Decision</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                <tr className="hover:bg-slate-800/30 transition">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-200">
                      {ILLUSTRATIVE_DEMO_EXPERIMENT.name}
                    </div>
                    <div className="text-[11px] text-amber-400/90 flex items-center gap-1 mt-0.5">
                      <AlertTriangle className="h-3 w-3" /> Illustrative Demo Preview
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    <div>{ILLUSTRATIVE_DEMO_EXPERIMENT.model.name}</div>
                    <div className="text-[11px] text-slate-400">SST-2 (500 samples)</div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 font-mono text-[11px]">
                      {ILLUSTRATIVE_DEMO_EXPERIMENT.optimizationMethod}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-emerald-400 font-semibold">
                    -74.9% (268MB → 67MB)
                  </td>
                  <td className="py-3 px-3 text-emerald-400 font-semibold">
                    -41.9% (14.8ms → 8.6ms)
                  </td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold text-[11px]">
                      <CheckCircle2 className="h-3 w-3" /> ACCEPTED
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => setActiveTab("comparison")}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    >
                      Inspect Comparison
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : experiments.length === 0 ? (
          <div className="py-16 text-center">
            <div className="h-12 w-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
              <Clock className="h-6 w-6" />
            </div>
            <h4 className="mt-4 text-sm font-semibold text-white">No Experiments Recorded Yet</h4>
            <p className="mt-1 text-xs text-slate-400 max-w-md mx-auto">
              Your SQLite database is clean. No model runs have been created.
              Configure a new experiment run, or toggle the illustrative preview to explore the comparison screens.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={() => setActiveTab("setup")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow transition"
              >
                Configure Experiment
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setIsIllustrativeActive(true)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-medium transition"
              >
                View Illustrative Preview
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-3 px-3">Experiment ID & Name</th>
                  <th className="py-3 px-3">Model</th>
                  <th className="py-3 px-3">Task</th>
                  <th className="py-3 px-3">Method</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Created</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {experiments.map((exp) => (
                  <tr key={exp.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-200">{exp.name}</div>
                      <div className="font-mono text-[10px] text-slate-400">{exp.id}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-300 font-mono text-[11px]">
                      {exp.model_id}
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {exp.task}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 font-mono text-[11px]">
                        {exp.optimization_method}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold text-[11px] ${
                          exp.status === "completed"
                            ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                            : exp.status === "queued" || exp.status === "validating" || exp.status === "profiling"
                            ? "bg-blue-500/10 border border-blue-500/30 text-blue-400"
                            : exp.status === "cancelled"
                            ? "bg-slate-700 text-slate-300"
                            : exp.status === "failed"
                            ? "bg-red-500/10 border border-red-500/30 text-red-400"
                            : "bg-amber-500/10 border border-amber-500/30 text-amber-300"
                        }`}
                      >
                        {exp.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400 text-[11px]">
                      {exp.created_at}
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      {exp.status !== "completed" && exp.status !== "failed" && exp.status !== "cancelled" && (
                        <button
                          onClick={() => handleCancel(exp.id)}
                          disabled={actionInProgress === exp.id}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-red-950/40 text-red-400 hover:text-red-300 border border-slate-700 text-[11px] transition"
                        >
                          {actionInProgress === exp.id ? "Cancelling..." : "Cancel"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
