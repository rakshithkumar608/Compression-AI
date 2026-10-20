"use client";

import React, { useState } from "react";
import { Leaf, AlertCircle, ShieldCheck, HelpCircle, Calculator, Info } from "lucide-react";

export const EnvironmentalView: React.FC = () => {
  const [testJoules, setTestJoules] = useState<number>(100);
  const [gridIntensity, setGridIntensity] = useState<number>(480); // gCO2/kWh

  // Conversion: Joules -> kWh -> gCO2
  const kwh = testJoules / 3_600_000;
  const emissionsGrams = kwh * gridIntensity;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Environmental & Resource Measurement Methodology</h2>
        <p className="text-xs text-slate-400 mt-1">
          EcoCompress AI operates under a strict anti-greenwashing transparency protocol. Never invent or inflate savings.
        </p>
      </div>

      {/* Ethical Reporting Principles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Measured */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-2">
          <div className="flex items-center gap-2">
            <span className="h-6 w-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
              M
            </span>
            <h3 className="text-sm font-semibold text-white">Measured Metrics</h3>
          </div>
          <p className="text-xs text-slate-300">
            Energy consumption is labeled <strong>Measured</strong> ONLY when retrieved from physical device meters or GPU vendor sensor interfaces (e.g. NVIDIA NVML power counters).
          </p>
          <div className="pt-2 text-[11px] text-emerald-400 font-medium">
            Requires hardware sensor telemetry.
          </div>
        </div>

        {/* Card 2: Estimated */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-2">
          <div className="flex items-center gap-2">
            <span className="h-6 w-6 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs">
              E
            </span>
            <h3 className="text-sm font-semibold text-white">Estimated Metrics</h3>
          </div>
          <p className="text-xs text-slate-300">
            Carbon emissions are labeled <strong>Estimated</strong> because they depend on mathematical conversion of measured electrical energy against regional power grid carbon intensity factors.
          </p>
          <div className="pt-2 text-[11px] text-blue-400 font-medium">
            Documented formula & regional grid constants.
          </div>
        </div>

        {/* Card 3: Unavailable (Water Policy) */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-2">
          <div className="flex items-center gap-2">
            <span className="h-6 w-6 rounded-full bg-slate-700 text-slate-300 flex items-center justify-center font-bold text-xs">
              U
            </span>
            <h3 className="text-sm font-semibold text-white">Unavailable Metrics (Water)</h3>
          </div>
          <p className="text-xs text-slate-300">
            Direct water consumption is marked <strong>Unavailable</strong> in MVP. The system will NEVER infer water usage from GPU runtime alone without physical datacenter cooling telemetry.
          </p>
          <div className="pt-2 text-[11px] text-slate-400 font-medium">
            Strict anti-fabrication product rule (§2).
          </div>
        </div>
      </div>

      {/* Interactive Carbon Conversion Formula */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Calculator className="h-4 w-4 text-emerald-400" />
          <span>Interactive Carbon Emission Estimator</span>
        </div>
        <p className="text-xs text-slate-300">
          Explore how measured inference Joules map to estimated greenhouse gas emissions (gCO₂e):
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Measured Energy (Joules)</label>
            <input
              type="number"
              value={testJoules}
              onChange={(e) => setTestJoules(Number(e.target.value))}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white text-xs font-mono focus:outline-none focus:border-emerald-500"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">
              = {(testJoules / 3_600_000).toExponential(3)} kWh
            </span>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Grid Carbon Intensity (gCO₂/kWh)</label>
            <select
              value={gridIntensity}
              onChange={(e) => setGridIntensity(Number(e.target.value))}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="50">Nordics / Clean Hydro (50 gCO₂/kWh)</option>
              <option value="250">European Grid Average (250 gCO₂/kWh)</option>
              <option value="380">US National Average (380 gCO₂/kWh)</option>
              <option value="480">Global Benchmark Average (480 gCO₂/kWh)</option>
              <option value="720">Fossil-Heavy Grid (720 gCO₂/kWh)</option>
            </select>
          </div>

          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col justify-center">
            <span className="text-[11px] text-emerald-400 font-medium">Estimated Emissions</span>
            <span className="text-xl font-bold text-white font-mono mt-0.5">
              {emissionsGrams < 0.001 ? emissionsGrams.toExponential(3) : emissionsGrams.toFixed(4)} gCO₂e
            </span>
          </div>
        </div>
      </div>

      {/* Water Footprint Anti-Greenwashing Statement */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white">Why Water Consumption is Unavailable in MVP</h3>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Datacenter water cooling varies by up to <strong>100x</strong> depending on location, outdoor wet-bulb temperature, facility chiller technology, and power generation source. 
          Generating arbitrary milliliter numbers from model parameter counts or inference execution time is fundamentally inaccurate.
        </p>
        <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-800 text-[11px] text-slate-400">
          <strong className="text-slate-300">EcoCompress AI Guarantee:</strong> If a valid water metering interface or peer-reviewed regional methodology is introduced in a future phase, it will be transparently documented and peer-reviewable. Until then, the metric remains strictly marked as <code className="text-slate-300">Unavailable</code>.
        </div>
      </div>
    </div>
  );
};
