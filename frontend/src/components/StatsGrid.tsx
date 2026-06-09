"use client";

import type { DashboardStats } from "@/lib/api";

const STAT_CONFIG = [
  { key: "pending", label: "Pending", className: "stat-pending" },
  { key: "processing", label: "Processing", className: "stat-processing" },
  { key: "completed", label: "Completed", className: "stat-completed" },
  { key: "failed", label: "Failed", className: "stat-failed" },
  { key: "cancelled", label: "Cancelled", className: "stat-cancelled" },
  { key: "dlq", label: "DLQ", className: "stat-dlq" },
] as const;

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  return (
    <div className="stats-grid">
      {STAT_CONFIG.map(({ key, label, className }) => (
        <div key={key} className={`stat-card ${className}`}>
          <div className="value">{stats[key]}</div>
          <div className="label">{label}</div>
        </div>
      ))}
    </div>
  );
}
