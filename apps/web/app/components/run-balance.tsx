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
        const response = await fetch(apiUrl("/api/usage"), { credentials: "include" });
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
    <Link href="/pay" className="hidden min-h-11 items-center rounded-2xl bg-green-50 px-4 py-2 text-base font-semibold text-green-900 focus:outline-none focus:ring-2 focus:ring-green-700 md:inline-flex">
      Запуски: {paidRuns}
    </Link>
  ) : (
    <Link href="/pay" className="hidden min-h-11 items-center rounded-2xl border border-blue-200 px-4 py-2 text-base font-semibold text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-700 md:inline-flex">
      Купить запуск
    </Link>
  );
}

