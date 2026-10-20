"use client";

import React from "react";
import { Cpu, HardDrive, Play, ArrowRight, AlertTriangle, Layers, CheckCircle2, Clock } from "lucide-react";
import { HOST_SYSTEM_DIAGNOSTICS, ILLUSTRATIVE_DEMO_EXPERIMENT } from "@/lib/illustrativeData";
import { NavTab } from "./Sidebar";

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
            EcoCompress AI measures whether an optimized model retains task quality while reducing memory, latency, and energy footprint.
            All experiments execute under identical, deterministic test workloads with strict acceptance threshold gating.
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
            <span className="text-xs font-medium text-slate-400">D: Storage (Artifacts & Caches)</span>
            <HardDrive className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-emerald-400">
            {HOST_SYSTEM_DIAGNOSTICS.dDriveFreeGb} GB
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Healthy free storage on primary drive
          </p>
          <div className="mt-3 text-[11px] text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> All ML caches redirected here
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
            <h3 className="text-lg font-semibold text-white">Recent Experiments & Benchmark Runs</h3>
            <p className="text-xs text-slate-400">
              Deterministic evaluation history stored in SQLite (`data/ecocompress.db`)
            </p>
          </div>
          <div className="flex items-center gap-2">
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

        {/* Empty State vs Illustrative Experiment Table */}
        {!isIllustrativeActive ? (
          <div className="py-16 text-center">
            <div className="h-12 w-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
              <Clock className="h-6 w-6" />
            </div>
            <h4 className="mt-4 text-sm font-semibold text-white">No Experiments Recorded Yet</h4>
            <p className="mt-1 text-xs text-slate-400 max-w-md mx-auto">
              Your SQLite database is clean. No model runs have been queued.
              Set up your first baseline & candidate benchmark, or toggle the illustrative preview to explore the comparison screens.
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
        )}
      </div>
    </div>
  );
};
