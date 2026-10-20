"use client";

import React from "react";
import { Cpu, HardDrive, ShieldCheck, Activity } from "lucide-react";
import { HOST_SYSTEM_DIAGNOSTICS } from "@/lib/illustrativeData";

interface HeaderProps {
  isIllustrativeActive: boolean;
  setIsIllustrativeActive: (val: boolean) => void;
}

export const Header: React.FC<HeaderProps> = ({
  isIllustrativeActive,
  setIsIllustrativeActive,
}) => {
  return (
    <header className="border-b border-slate-800 bg-[#0e1626]/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Brand & Phase Title */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-lg shadow-sm">
            🍃
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg tracking-tight text-white">EcoCompress AI</span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                Phase 1 MVP
              </span>
            </div>
            <p className="text-xs text-slate-400">Evidence-Based Model Compression & Benchmarking Workbench</p>
          </div>
        </div>

        {/* Hardware Status Strip */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* GPU Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <Cpu className="h-3.5 w-3.5 text-blue-400" />
            <span className="font-medium text-slate-200">RTX 2050 (4 GB)</span>
          </div>

          {/* D: Drive Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <HardDrive className="h-3.5 w-3.5 text-emerald-400" />
            <span>D: <strong className="text-emerald-400">{HOST_SYSTEM_DIAGNOSTICS.dDriveFreeGb} GB</strong> Free</span>
          </div>

          {/* C: Drive Safety Guard Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
            <span>C: Protected (<strong className="text-amber-400">{HOST_SYSTEM_DIAGNOSTICS.cDriveFreeMb} MB</strong>)</span>
          </div>

          {/* Illustrative Preview Toggle */}
          <div className="flex items-center gap-2 ml-2 pl-3 border-l border-slate-700/60">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <span className="text-xs text-slate-400 font-medium">Illustrative Preview</span>
              <input
                type="checkbox"
                checked={isIllustrativeActive}
                onChange={(e) => setIsIllustrativeActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-600 relative"></div>
            </label>
          </div>
        </div>
      </div>
    </header>
  );
};
