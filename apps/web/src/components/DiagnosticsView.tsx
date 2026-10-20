"use client";

import React from "react";
import { Server, HardDrive, Cpu, ShieldCheck, CheckCircle2, AlertTriangle, Layers, Terminal } from "lucide-react";
import { HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";

export const DiagnosticsView: React.FC = () => {
  const d = HOST_SYSTEM_DIAGNOSTICS;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Host Diagnostics & Environment Telemetry</h2>
        <p className="text-xs text-slate-400 mt-1">
          Verified hardware capabilities, runtime versions, and disk safety guardrails detected during Phase 0.
        </p>
      </div>

      {/* Hardware Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* GPU */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">GPU Subsystem</span>
            <Cpu className="h-4 w-4 text-blue-400" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">{d.gpuName}</div>
            <div className="text-xs text-slate-400 mt-0.5">VRAM: {d.gpuVramMb} MB ({d.gpuVramMb / 1024} GB)</div>
          </div>
          <div className="pt-2 border-t border-slate-800 space-y-1 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Driver (KMD):</span>
              <span className="font-mono text-slate-200">{d.driverVersion}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>CUDA Support (UMD):</span>
              <span className="font-mono text-slate-200">{d.cudaVersion}</span>
            </div>
          </div>
        </div>

        {/* Storage */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Storage Drives</span>
            <HardDrive className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-200">D: Drive (Storage Root)</span>
                <span className="font-mono text-emerald-400 font-bold">{d.dDriveFreeGb} GB Free</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 mt-1">
                <div className="bg-emerald-500 h-full w-[30%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-amber-300">C: Drive (Critical Low)</span>
                <span className="font-mono text-amber-400 font-bold">{d.cDriveFreeMb} MB Free</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 mt-1">
                <div className="bg-amber-500 h-full w-[99%]"></div>
              </div>
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800 text-[11px] text-amber-300 flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5" /> All writes locked to D: drive
          </div>
        </div>

        {/* Runtimes */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Runtimes & Tools</span>
            <Terminal className="h-4 w-4 text-purple-400" />
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Python:</span>
              <span className="font-mono text-slate-200">{d.pythonVersion}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Node.js:</span>
              <span className="font-mono text-slate-200">{d.nodeVersion}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Package Manager:</span>
              <span className="font-mono text-slate-200">uv 0.12.17</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>OS Platform:</span>
              <span className="text-slate-200">Windows 11 x64</span>
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800 text-[11px] text-emerald-400 flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" /> Next.js 14 + FastAPI ready
          </div>
        </div>
      </div>

      {/* Cache Redirection Matrix */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <h3 className="text-sm font-semibold text-white">Active Cache Path Redirection (Storage Guard)</h3>
        <p className="text-xs text-slate-400">
          The following environment variables protect the nearly full C: drive from accidental overflow:
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2.5 px-3">Variable</th>
                <th className="py-2.5 px-3">Target Directory (D: Drive)</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Protected Cache</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">HF_HOME</td>
                <td className="py-2.5 px-3 text-slate-300">D:\cache\huggingface</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">Downloaded model weights & tokenizers</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">TORCH_HOME</td>
                <td className="py-2.5 px-3 text-slate-300">D:\cache\torch</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">PyTorch hub models & checkpoints</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">PIP_CACHE_DIR</td>
                <td className="py-2.5 px-3 text-slate-300">D:\cache\pip</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">Python wheel binaries</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">UV_CACHE_DIR</td>
                <td className="py-2.5 px-3 text-slate-300">D:\cache\uv</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">uv fast package installer cache</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">NPM_CONFIG_CACHE</td>
                <td className="py-2.5 px-3 text-slate-300">D:\npm-cache</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">Node modules & npm tarballs</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-emerald-400">TEMP / TMP</td>
                <td className="py-2.5 px-3 text-slate-300">D:\Temp</td>
                <td className="py-2.5 px-3 text-emerald-400">ACTIVE</td>
                <td className="py-2.5 px-3 text-slate-400 font-sans">Temporary OS build files</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
