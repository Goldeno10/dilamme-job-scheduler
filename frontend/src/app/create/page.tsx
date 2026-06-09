"use client";

import { useState } from "react";
import { api, type Priority, type RecurringInterval } from "@/lib/api";

export default function CreateJobPage() {
  const [type, setType] = useState("send_email");
  const [priority, setPriority] = useState<Priority>(2);
  const [payload, setPayload] = useState('{"to": "test@gmail.com", "subject": "Welcome"}');
  const [scheduledAt, setScheduledAt] = useState("");
  const [interval, setInterval] = useState<RecurringInterval | "">("");
  const [dependsOn, setDependsOn] = useState("");
  const [workflowEmail, setWorkflowEmail] = useState("test@gmail.com");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(payload);
      } catch {
        throw new Error("Invalid JSON payload");
      }

      const job = await api.createJob({
        type,
        payload: parsed,
        priority,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
        interval: interval || undefined,
        depends_on: dependsOn ? dependsOn.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
      });
      setMessage(`Job created: ${job.id}`);
    } catch (err) {
      setMessage(`Error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleWorkflow = async () => {
    setLoading(true);
    setMessage("");
    try {
      const jobs = await api.createReportWorkflow(workflowEmail);
      setMessage(`DAG workflow created: ${jobs.map((j) => j.id.slice(0, 8)).join(" → ")}`);
    } catch (err) {
      setMessage(`Error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>Create Job</h1>

      <div className="card">
        <h2>New Job</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div>
              <label>Type</label>
              <select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="send_email">send_email</option>
                <option value="webhook">webhook</option>
                <option value="generate_report">generate_report</option>
                <option value="upload_file">upload_file</option>
              </select>
            </div>
            <div>
              <label>Priority</label>
              <select value={priority} onChange={(e) => setPriority(Number(e.target.value) as Priority)}>
                <option value={1}>High (1)</option>
                <option value={2}>Medium (2)</option>
                <option value={3}>Low (3)</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div>
              <label>Scheduled At (optional)</label>
              <input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
            </div>
            <div>
              <label>Recurring Interval (optional)</label>
              <select value={interval} onChange={(e) => setInterval(e.target.value as RecurringInterval | "")}>
                <option value="">None</option>
                <option value="every_1_minute">every_1_minute</option>
                <option value="every_5_minutes">every_5_minutes</option>
                <option value="every_1_hour">every_1_hour</option>
              </select>
            </div>
          </div>

          <div>
            <label>Depends On (comma-separated job IDs)</label>
            <input value={dependsOn} onChange={(e) => setDependsOn(e.target.value)} placeholder="uuid1, uuid2" />
          </div>

          <div>
            <label>Payload (JSON)</label>
            <textarea value={payload} onChange={(e) => setPayload(e.target.value)} />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Creating…" : "Create Job"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>DAG Workflow: Report Pipeline</h2>
        <p style={{ color: "var(--muted)", marginBottom: "1rem", fontSize: "0.875rem" }}>
          Generate Report → Upload File → Send Email
        </p>
        <div style={{ display: "flex", gap: "1rem", alignItems: "end" }}>
          <div style={{ flex: 1 }}>
            <label>Email recipient</label>
            <input value={workflowEmail} onChange={(e) => setWorkflowEmail(e.target.value)} />
          </div>
          <button className="btn-secondary" onClick={handleWorkflow} disabled={loading}>
            Create Workflow
          </button>
        </div>
      </div>

      {message && (
        <div className="card" style={{ color: message.startsWith("Error") ? "var(--danger)" : "var(--success)" }}>
          {message}
        </div>
      )}
    </div>
  );
}
