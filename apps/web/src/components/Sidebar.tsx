"use client";

import React from "react";
import { LayoutDashboard, Box, PlayCircle, BarChart3, Leaf, Server } from "lucide-react";

export type NavTab = "overview" | "models" | "setup" | "comparison" | "environment" | "diagnostics";

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: "overview", label: "Dashboard Overview", icon: LayoutDashboard },
    { id: "models", label: "Model Workspace", icon: Box },
    { id: "setup", label: "New Experiment", icon: PlayCircle },
    { id: "comparison", label: "Compare & Decide", icon: BarChart3 },
    { id: "environment", label: "Environmental Metrics", icon: Leaf },
    { id: "diagnostics", label: "Host Diagnostics", icon: Server },
  ] as const;

  return (
    <aside className="w-full md:w-64 border-r border-slate-800 bg-[#0d1424] flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                isActive
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/50"
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-8 pt-4 border-t border-slate-800/80 text-[11px] text-slate-400 space-y-1.5 px-3">
        <p className="font-semibold text-slate-300">Phase 1 Guardrails Active</p>
        <p>• Model processing decoupled</p>
        <p>• No fake or invented metrics</p>
        <p>• Heavy operations strictly on D:</p>
      </div>
    </aside>
  );
};
