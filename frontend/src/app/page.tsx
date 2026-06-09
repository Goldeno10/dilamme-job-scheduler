"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type DashboardStats } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { StatsGrid } from "@/components/StatsGrid";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [alert, setAlert] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStats(await api.getStats());
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useSSE(useCallback((event, data) => {
    refresh();
    if (event === "dlq_alert") {
      setAlert(`DLQ alert: ${data.dlq_count} jobs exceeded threshold of ${data.threshold}`);
    }
  }, [refresh]));

  return (
    <div>
      <h1 style={{ marginBottom: "0.5rem" }}>
        <span className="live-dot" />
        Dashboard
      </h1>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
        Live updates via Server-Sent Events
      </p>

      {alert && <div className="alert">{alert}</div>}

      {stats ? <StatsGrid stats={stats} /> : <p>Loading stats…</p>}
    </div>
  );
}
