"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Job, type JobStatus } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { JobsTable } from "@/components/JobsTable";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      setJobs(await api.getJobs((filter || undefined) as JobStatus | undefined));
    } catch (e) {
      console.error(e);
    }
  }, [filter]);

  useEffect(() => { refresh(); }, [refresh]);
  useSSE(useCallback(() => { refresh(); }, [refresh]));

  const handleCancel = async (id: string) => {
    try {
      await api.cancelJob(id);
      refresh();
    } catch (e) {
      alert(String(e));
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: "1rem" }}>Jobs</h1>
      <div style={{ marginBottom: "1rem" }}>
        <label>Filter by status</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
      <JobsTable jobs={jobs} onCancel={handleCancel} />
    </div>
  );
}
