"use client";

import { useEffect, useRef, useState } from "react";
import type { Contest } from "../lib/product-registry";

export function ContestChips({ contests }: { contests: Contest[] }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [open]);

  if (contests.length <= 4) {
    return (
      <div className="mt-3 flex flex-wrap gap-2" aria-label="Подходит для">
        {contests.map((contest) => (
          <span key={contest.slug} className="rounded-full bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-900">
            {contest.short_name}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="relative mt-3">
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onMouseEnter={() => setOpen(true)}
        className="min-h-11 rounded-full bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-700"
      >
        {contests.length} конкурсов
      </button>
      {open ? (
        <div role="dialog" aria-label="Список конкурсов" className="absolute left-0 top-full z-20 mt-2 min-w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
          {contests.map((contest) => <p key={contest.slug} className="px-2 py-2 text-sm">{contest.name}</p>)}
        </div>
      ) : null}
    </div>
  );
}
