"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export type ModuleStep = { id: string; label: string; disabled?: boolean };

export function ModuleShell({
  steps,
  children,
  utility,
  helpSlot,
  faqSlot,
  contextualHelpSlot,
  expertSlot,
}: {
  steps: ModuleStep[];
  children: ReactNode;
  utility?: ReactNode;
  helpSlot?: ReactNode;
  faqSlot?: ReactNode;
  contextualHelpSlot?: ReactNode;
  expertSlot?: ReactNode;
}) {
  const [activeId, setActiveId] = useState(steps[0]?.id || "");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const activeIndex = Math.max(0, steps.findIndex((step) => step.id === activeId));

  useEffect(() => {
    const elements = steps
      .map((step) => document.getElementById(step.id))
      .filter((element): element is HTMLElement => Boolean(element));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible?.target.id) setActiveId(visible.target.id);
      },
      { rootMargin: "-22% 0px -65% 0px", threshold: [0, 0.1] },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [steps]);

  useEffect(() => {
    if (!drawerOpen) return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [drawerOpen]);

  function goTo(step: ModuleStep) {
    if (step.disabled) return;
    document.getElementById(step.id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveId(step.id);
    setDrawerOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-5 flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-3 lg:hidden">
        <span className="text-base font-semibold">Этап {activeIndex + 1} из {steps.length}</span>
        <button
          ref={triggerRef}
          type="button"
          aria-expanded={drawerOpen}
          aria-controls="module-stages-drawer"
          onClick={() => setDrawerOpen(true)}
          className="min-h-11 rounded-xl border border-blue-800 px-4 py-2 text-base font-semibold text-blue-800"
        >
          Этапы
        </button>
      </div>

      <div className="grid min-w-0 gap-8 lg:grid-cols-[220px_minmax(0,820px)] xl:grid-cols-[220px_minmax(0,820px)_260px]">
        <nav aria-label="Этапы модуля" className="hidden lg:block">
          <ol className="sticky top-28 grid gap-2">
            {steps.map((step, index) => (
              <li key={step.id}>
                <button
                  type="button"
                  disabled={step.disabled}
                  onClick={() => goTo(step)}
                  className={`min-h-11 w-full rounded-xl px-3 py-2 text-left text-base font-semibold ${
                    activeId === step.id ? "bg-blue-50 text-blue-900" : "text-slate-600 hover:bg-slate-100"
                  } disabled:cursor-not-allowed disabled:text-slate-400`}
                >
                  {index + 1}. {step.label}
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <div className="min-w-0">{children}</div>
        <aside className="hidden xl:block">{utility}</aside>
      </div>

      {drawerOpen ? (
        <div
          className="fixed inset-0 z-50 bg-slate-950/35"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setDrawerOpen(false);
              triggerRef.current?.focus();
            }
          }}
        >
          <div id="module-stages-drawer" role="dialog" aria-modal="true" aria-label="Этапы модуля" className="absolute inset-x-0 bottom-0 rounded-t-3xl bg-white p-5 shadow-2xl">
            <p className="text-2xl font-bold">Этапы</p>
            <div className="mt-4 grid gap-2">
              {steps.map((step, index) => (
                <button key={step.id} type="button" disabled={step.disabled} onClick={() => goTo(step)} className="min-h-12 rounded-2xl bg-slate-50 px-4 py-3 text-left text-base font-semibold disabled:text-slate-400">
                  {index + 1}. {step.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}
      {helpSlot}{faqSlot}{contextualHelpSlot}{expertSlot}
    </div>
  );
}

