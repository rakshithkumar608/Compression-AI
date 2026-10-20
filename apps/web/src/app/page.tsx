"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { Sidebar, NavTab } from "@/components/Sidebar";
import { DashboardView } from "@/components/DashboardView";
import { ModelWorkspaceView } from "@/components/ModelWorkspaceView";
import { ExperimentSetupView } from "@/components/ExperimentSetupView";
import { ComparisonView } from "@/components/ComparisonView";
import { EnvironmentalView } from "@/components/EnvironmentalView";
import { DiagnosticsView } from "@/components/DiagnosticsView";
import { ModelProfile } from "@/types";

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [isIllustrativeActive, setIsIllustrativeActive] = useState(false);
  const [selectedModelForSetup, setSelectedModelForSetup] = useState<ModelProfile | undefined>();

  const handleSelectModelForExperiment = (model: ModelProfile) => {
    setSelectedModelForSetup(model);
    setActiveTab("setup");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19]">
      {/* Top Application Header */}
      <Header
        isIllustrativeActive={isIllustrativeActive}
        setIsIllustrativeActive={setIsIllustrativeActive}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* Navigation Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Content View Container */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl overflow-y-auto">
          {activeTab === "overview" && (
            <DashboardView
              isIllustrativeActive={isIllustrativeActive}
              setIsIllustrativeActive={setIsIllustrativeActive}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === "models" && (
            <ModelWorkspaceView
              onSelectModelForExperiment={handleSelectModelForExperiment}
            />
          )}

          {activeTab === "setup" && (
            <ExperimentSetupView
              initialModel={selectedModelForSetup}
              onExperimentComplete={() => setActiveTab("overview")}
            />
          )}

          {activeTab === "comparison" && (
            <ComparisonView
              isIllustrativeActive={isIllustrativeActive}
              setIsIllustrativeActive={setIsIllustrativeActive}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === "environment" && <EnvironmentalView />}

          {activeTab === "diagnostics" && <DiagnosticsView />}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0d1424] px-6 py-3 text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-2">
          <span>EcoCompress AI • Phase 1 Foundation</span>
          <span>•</span>
          <span className="text-slate-300">Evidence-Based Model Benchmarks</span>
        </div>
        <div className="text-[11px] text-slate-400">
          Strict Anti-Greenwashing & Storage Protection Protocol Active
        </div>
      </footer>
    </div>
  );
}
