"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api-client";

export const USAGE_UPDATED_EVENT = "lary-usage-updated";

type UsageState = {
  paid_runs: number;
  modules: Record<string, { free_attempt_available: boolean; free_attempt_used: boolean }>;
};

export function ModuleAttemptStatus({ moduleSlug, className = "" }: { moduleSlug: string; className?: string }) {
  const [usage, setUsage] = useState<UsageState | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadUsage() {
      try {
        const response = await fetch(apiUrl("/api/usage"), { credentials: "include" });
        if (!response.ok) return;
        const payload = await response.json();
        if (!cancelled) setUsage(payload);
      } catch {
        if (!cancelled) setUsage(null);
      }
    }

    void loadUsage();
    window.addEventListener(USAGE_UPDATED_EVENT, loadUsage);
    return () => {
      cancelled = true;
      window.removeEventListener(USAGE_UPDATED_EVENT, loadUsage);
    };
  }, [moduleSlug]);

  const freeAvailable = usage?.modules?.[moduleSlug]?.free_attempt_available ?? true;
  const paidRuns = usage?.paid_runs ?? 0;
  const text = freeAvailable ? "1 бесплатный запуск в этом модуле" : paidRuns > 0 ? `доступно платных запусков: ${paidRuns}` : "необходимо купить запуск модуля";
  const tone = freeAvailable || paidRuns > 0 ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800";

  return <p className={`${className || "mt-5"} rounded-2xl p-4 text-base font-semibold leading-7 break-words ${tone}`}>{text}</p>;
}
