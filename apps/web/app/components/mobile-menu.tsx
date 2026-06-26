"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type NavItem = {
  label: string;
  href: string;
};

export function MobileMenu({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  function close() {
    setOpen(false);
  }

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="lary-mobile-menu"
        onClick={() => setOpen((current) => !current)}
        className="flex min-h-12 items-center gap-2 rounded-2xl border border-blue-800 bg-white px-4 py-2 text-base font-semibold text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
      >
        <span aria-hidden="true">{open ? "▲" : "▼"}</span>
        Меню
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[100] bg-slate-950/25 px-4 pt-24"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <div
            id="lary-mobile-menu"
            ref={panelRef}
            role="dialog"
            aria-label="Мобильное меню"
            className="mx-auto grid max-w-sm gap-2 rounded-3xl border border-slate-200 bg-white p-4 shadow-2xl"
            onMouseDown={(event) => event.stopPropagation()}
          >
            {items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                className="flex min-h-12 items-center rounded-2xl px-4 py-3 text-base font-semibold text-slate-900 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-700"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/modules"
              onClick={close}
              className="mt-2 flex min-h-12 items-center justify-center rounded-2xl bg-blue-800 px-5 py-3 text-base font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2"
            >
              Начать
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
