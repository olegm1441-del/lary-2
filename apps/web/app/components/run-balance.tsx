"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api-client";
import { USAGE_UPDATED_EVENT } from "./module-attempt-status";

export function RunBalance() {
  const [paidRuns, setPaidRuns] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch(apiUrl("/api/usage"), {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (active) setPaidRuns(Number(payload.paid_runs) || 0);
      } catch {
        if (active) setPaidRuns(null);
      }
    }
    void refresh();
    window.addEventListener(USAGE_UPDATED_EVENT, refresh);
    return () => {
      active = false;
      window.removeEventListener(USAGE_UPDATED_EVENT, refresh);
    };
  }, []);

  if (paidRuns === null) return null;
  return paidRuns > 0 ? (
    <Link href="/pay" className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-2xl bg-green-50 px-3 py-2 text-sm font-semibold text-green-900 focus:outline-none focus:ring-2 focus:ring-green-700 sm:text-base">
      <span className="sm:hidden">{paidRuns} {runWord(paidRuns)}</span>
      <span className="hidden sm:inline">Запуски: {paidRuns}</span>
    </Link>
  ) : (
    <Link href="/pay" className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-2xl border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-700 sm:text-base">
      Купить запуск
    </Link>
  );
}

function runWord(value: number) {
  const lastTwo = value % 100;
  const last = value % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return "запусков";
  if (last === 1) return "запуск";
  if (last >= 2 && last <= 4) return "запуска";
  return "запусков";
}
