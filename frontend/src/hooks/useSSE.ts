"use client";

import { useEffect, useRef, useCallback } from "react";
import { eventsUrl } from "@/lib/api";

type SSEHandler = (event: string, data: Record<string, unknown>) => void;

export function useSSE(onEvent: SSEHandler) {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  const stableHandler = useCallback((event: string, data: Record<string, unknown>) => {
    handlerRef.current(event, data);
  }, []);

  useEffect(() => {
    const url = eventsUrl();
    const source = new EventSource(url);

    const events = [
      "job_created",
      "job_started",
      "job_completed",
      "job_failed",
      "job_cancelled",
      "job_retry",
      "job_retried_from_dlq",
      "dlq_alert",
    ];

    for (const name of events) {
      source.addEventListener(name, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          stableHandler(name, data);
        } catch {
          /* ignore malformed */
        }
      });
    }

    source.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        stableHandler("message", data);
      } catch {
        /* ignore */
      }
    };

    source.onerror = () => {
      source.close();
      setTimeout(() => {
        /* browser auto-reconnects EventSource by default on new instance */
      }, 3000);
    };

    return () => source.close();
  }, [stableHandler]);
}
