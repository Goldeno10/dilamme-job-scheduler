"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Job } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { JobsTable } from "@/components/JobsTable";

export default function DlqPage() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const refresh = useCallback(async () => {
    try {
      setJobs(await api.getDlq());
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useSSE(useCallback(() => { refresh(); }, [refresh]));

  const handleRetry = async (id: string) => {
    try {
      await api.retryDlq(id);
      refresh();
    } catch (e) {
      alert(String(e));
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: "0.5rem" }}>Dead-Letter Queue</h1>
      <p style={{ color: "var(--muted)", marginBottom: "1.5rem", fontSize: "0.875rem" }}>
        Jobs that exhausted all retries. Alert fires when DLQ count reaches 5.
      </p>
      <JobsTable jobs={jobs} showError onRetry={handleRetry} />
    </div>
  );
}
