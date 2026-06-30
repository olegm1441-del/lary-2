"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { LaryModule } from "../lib/lary-data";
import { apiUrl, readApiError } from "../lib/api-client";
import { USAGE_UPDATED_EVENT } from "./module-attempt-status";

type UsagePayload = {
  paid_runs: number;
  modules: Record<string, { free_attempt_available: boolean; free_attempt_used: boolean }>;
};

type WorkloadMode = "percent" | "hours_total";
type SourceScope = "all" | "aggregators" | "official";
type CofinanceSource = "own_legal_entity_funds" | "partner_letter_funds";

type SalaryPositionDraft = {
  id: string;
  role_title: string;
  staff_count: string;
  duration_months: string;
  workload_mode: WorkloadMode;
  workload_value: string;
  functionality: string;
  calendar_events: string;
};

type SalaryDraft = {
  region: string;
  source_scope: SourceScope;
  cofinance_source: CofinanceSource | "";
  positions: SalaryPositionDraft[];
};

type SalaryGenerateResult = {
  run_id: string;
  status: string;
  module_slug: string;
  title: string;
  plain_text: string;
  total_amount: number;
  downloads: Record<string, string>;
  warnings: string[];
};

const STORAGE_KEY = "lary.module_draft.salary.v2";

const REGION_OPTIONS = ["Свердловская область", "Республика Татарстан", "Москва", "Санкт-Петербург", "Краснодарский край", "Нижегородская область"];

const SOURCE_OPTIONS: Array<{ value: SourceScope; label: string; hint: string }> = [
  {
    value: "all",
    label: "Все доступные",
    hint: "Искать по агрегаторам вакансий и официальной статистике, затем выбрать самый высокий подтвержденный показатель.",
  },
  {
    value: "aggregators",
    label: "Агрегаторы вакансий",
    hint: "Использовать источники с зарплатными предложениями по должности: ГородРабот, HH, Trudvsem, доступные адаптеры.",
  },
  {
    value: "official",
    label: "Официальная статистика",
    hint: "Использовать официальный региональный ориентир Росстат/ЕМИСС, если он доступен.",
  },
];

const COFINANCE_OPTIONS: Array<{ value: CofinanceSource; label: string }> = [
  { value: "own_legal_entity_funds", label: "Собственные средства юридического лица" },
  { value: "partner_letter_funds", label: "Привлеченные средства согласно письму поддержки" },
];

export function SalaryModuleRunner({ module }: { module: LaryModule }) {
  const [draft, setDraft] = useState<SalaryDraft>(() => loadInitialDraft());
  const [usage, setUsage] = useState<UsagePayload | null>(null);
  const [state, setState] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<SalaryGenerateResult | null>(null);

  const validationErrors = useMemo(() => validateDraft(draft), [draft]);
  const canSubmit = validationErrors.length === 0;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
      } catch {
        // Черновик — локальное удобство. Основной результат сохраняется backend-ом.
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [draft]);

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
  }, []);

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setMessage("");
    setResult(null);

    const errors = validateDraft(draft);
    if (errors.length) {
      setState("error");
      setMessage(errors[0]);
      return;
    }

    const freeAvailable = usage?.modules?.salary?.free_attempt_available ?? true;
    const paidRuns = usage?.paid_runs ?? 0;
    if (!freeAvailable && paidRuns <= 0) {
      setState("error");
      setMessage("Для повторного запуска необходимо купить запуск модуля или применить промокод.");
      return;
    }

    setState("submitting");
    setMessage("Ищем зарплатные данные и считаем...");
    try {
      const response = await fetch(apiUrl("/api/modules/salary/generate"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toApiPayload(draft)),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setResult(payload);
      setState("idle");
      setMessage("Расчет готов");
      window.dispatchEvent(new CustomEvent(USAGE_UPDATED_EVENT));
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Не получилось автоматически найти зарплатный ориентир. Данные сохранены. Попробуйте изменить должность или регион и запустить расчет еще раз.");
    }
  }

  function updateDraft<K extends keyof SalaryDraft>(key: K, value: SalaryDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updatePosition(id: string, patch: Partial<SalaryPositionDraft>) {
    setDraft((current) => ({
      ...current,
      positions: current.positions.map((position) => (position.id === id ? { ...position, ...patch } : position)),
    }));
  }

  function addPosition() {
    setDraft((current) => ({ ...current, positions: [...current.positions, defaultPosition()] }));
  }

  function duplicatePosition(id: string) {
    setDraft((current) => {
      const source = current.positions.find((position) => position.id === id);
      if (!source) return current;
      return { ...current, positions: [...current.positions, { ...source, id: draftId() }] };
    });
  }

  function removePosition(id: string) {
    setDraft((current) => {
      if (current.positions.length <= 1) return current;
      return { ...current, positions: current.positions.filter((position) => position.id !== id) };
    });
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="mt-6 grid gap-5">
      <section className="rounded-3xl border border-slate-200 bg-white p-5">
        <h3 className="text-2xl font-bold text-slate-950">Заполните расчет по должностям</h3>
        <p className="mt-2 text-base leading-7 text-slate-600">
          Добавьте одну или несколько должностей. Лари проверит доступные источники зарплат, выберет самый высокий подтвержденный показатель и соберет расчет с обоснованием.
        </p>

        <div className="mt-5 grid gap-5">
          <FieldBlock label="Регион" required hint="Выберите регион, по которому нужно найти зарплатный ориентир.">
            <input
              list="salary-region-options"
              value={draft.region}
              onChange={(event) => updateDraft("region", event.target.value)}
              className={inputClassName}
              placeholder="Например: Свердловская область"
            />
            <datalist id="salary-region-options">
              {REGION_OPTIONS.map((region) => (
                <option key={region} value={region} />
              ))}
            </datalist>
            {!draft.region.trim() ? <InlineError>Выберите регион расчета.</InlineError> : null}
          </FieldBlock>

          <FieldBlock label="База расчета" required hint="Лари проверит доступные источники и выберет самый высокий подтвержденный показатель из выбранной группы.">
            <div className="grid gap-3">
              {SOURCE_OPTIONS.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  onClick={() => updateDraft("source_scope", option.value)}
                  className={`rounded-2xl border p-4 text-left ${draft.source_scope === option.value ? "border-blue-800 bg-blue-50" : "border-slate-300 bg-white"}`}
                  aria-pressed={draft.source_scope === option.value}
                >
                  <span className="block text-lg font-bold">{option.label}</span>
                  <span className="mt-1 block text-base leading-7 text-slate-600">{option.hint}</span>
                </button>
              ))}
            </div>
          </FieldBlock>

          <FieldBlock label="Софинансирование" required hint="Этот текст попадет в обоснование источника софинансирования.">
            <div className="grid gap-3 sm:grid-cols-2">
              {COFINANCE_OPTIONS.map((option) => (
                <label key={option.value} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border p-4 ${draft.cofinance_source === option.value ? "border-blue-800 bg-blue-50" : "border-slate-300 bg-white"}`}>
                  <input
                    type="radio"
                    name="cofinance_source"
                    value={option.value}
                    checked={draft.cofinance_source === option.value}
                    onChange={(event) => updateDraft("cofinance_source", event.target.value as CofinanceSource)}
                  />
                  <span className="font-semibold">{option.label}</span>
                </label>
              ))}
            </div>
            {!draft.cofinance_source ? <InlineError>Выберите источник софинансирования.</InlineError> : null}
          </FieldBlock>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-2xl font-bold text-slate-950">Позиции расчета</h3>
            <p className="mt-2 max-w-3xl text-base leading-7 text-slate-600">
              Добавьте одну или несколько должностей. Лари рассчитает каждую позицию отдельно и соберет общий итог.
            </p>
          </div>
          <button type="button" onClick={addPosition} className="min-h-12 rounded-2xl border border-blue-800 px-5 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50">
            Добавить должность
          </button>
        </div>

        <div className="mt-5 grid gap-5">
          {draft.positions.map((position, index) => (
            <PositionCard
              key={position.id}
              index={index}
              position={position}
              canDelete={draft.positions.length > 1}
              onChange={(patch) => updatePosition(position.id, patch)}
              onDuplicate={() => duplicatePosition(position.id)}
              onRemove={() => removePosition(position.id)}
            />
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6">
        <p className={`rounded-2xl p-4 text-base leading-7 ${canSubmit ? "bg-green-50 text-green-900" : "bg-red-50 text-red-900"}`}>
          {canSubmit ? "Все обязательные поля заполнены." : validationErrors[0]}
        </p>
        <button
          type="submit"
          disabled={state === "submitting"}
          className="mt-4 min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state === "submitting" ? "Ищем зарплатные данные и считаем..." : salaryButtonLabel(usage)}
        </button>
        {message ? <p className={`mt-4 rounded-2xl p-4 text-base leading-7 ${state === "error" ? "bg-red-50 text-red-900" : "bg-green-50 text-green-900"}`}>{message}</p> : null}
      </section>

      {result ? <SalaryResultBlock result={result} onRerun={() => void submit()} /> : null}
      <p className="sr-only">{module.shortTitle}</p>
    </form>
  );
}

function PositionCard({
  index,
  position,
  canDelete,
  onChange,
  onDuplicate,
  onRemove,
}: {
  index: number;
  position: SalaryPositionDraft;
  canDelete: boolean;
  onChange: (patch: Partial<SalaryPositionDraft>) => void;
  onDuplicate: () => void;
  onRemove: () => void;
}) {
  const workloadLabel = position.workload_mode === "hours_total" ? "Часы за весь проект на одного сотрудника" : "Занятость одного сотрудника, %";
  const workloadHint =
    position.workload_mode === "hours_total"
      ? "Например: 96. Лари рассчитает почасовую ставку от месячной зарплаты, принимая норму 160 часов в месяц."
      : "Например: 40. Формула: зарплата × 40% × месяцы × количество сотрудников.";

  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-xl font-bold text-slate-950">Должность {index + 1}</h4>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onDuplicate} className="min-h-11 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-900 hover:bg-blue-50">
            Дублировать
          </button>
          <button
            type="button"
            onClick={onRemove}
            disabled={!canDelete}
            className="min-h-11 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-900 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-slate-400"
          >
            Удалить
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-5">
        <FieldBlock label="Должность в проекте" required hint="Напишите должность так, как она будет в бюджете проекта. Лари сам попробует найти подходящие зарплатные данные и смежные названия.">
          <input className={inputClassName} value={position.role_title} onChange={(event) => onChange({ role_title: event.target.value })} placeholder="Например: координатор проекта" />
        </FieldBlock>

        <div className="grid gap-5 sm:grid-cols-2">
          <FieldBlock label="Количество сотрудников в этой роли" required hint="Если несколько человек выполняют одинаковую роль с одинаковой занятостью, укажите их количество здесь.">
            <input className={inputClassName} type="number" min={1} value={position.staff_count} onChange={(event) => onChange({ staff_count: event.target.value })} />
          </FieldBlock>
          <FieldBlock label="Срок работы в проекте, месяцев" required hint="Укажите только период работы в рамках проекта.">
            <input className={inputClassName} type="number" min={1} step="0.5" value={position.duration_months} onChange={(event) => onChange({ duration_months: event.target.value })} />
          </FieldBlock>
        </div>

        <FieldBlock label="Как считать занятость" required hint="Выберите процент занятости за месяц или общее число часов за весь проект.">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["percent", "% времени"],
              ["hours_total", "Часы за весь проект"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => onChange({ workload_mode: value as WorkloadMode, workload_value: "" })}
                className={`min-h-14 rounded-2xl border px-4 py-3 text-base font-semibold ${position.workload_mode === value ? "border-blue-800 bg-blue-50 text-blue-900" : "border-slate-300 bg-white text-slate-700"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </FieldBlock>

        <FieldBlock label={workloadLabel} required hint={workloadHint}>
          <input className={inputClassName} type="number" min={1} max={position.workload_mode === "percent" ? 100 : undefined} value={position.workload_value} onChange={(event) => onChange({ workload_value: event.target.value })} />
        </FieldBlock>

        <FieldBlock label="Что делает сотрудник" hint="Можно написать коротко. Если оставить пустым, Лари предложит типовой функционал по должности.">
          <textarea className={`${inputClassName} min-h-32`} value={position.functionality} onChange={(event) => onChange({ functionality: event.target.value })} placeholder="Например: ведет списки участников, согласует расписание, собирает обратную связь" />
        </FieldBlock>

        <FieldBlock label="Мероприятия календарного плана" hint="Необязательно. Если номера пока неизвестны, оставьте поле пустым — Лари поставит пометку для ручной вставки.">
          <input className={inputClassName} value={position.calendar_events} onChange={(event) => onChange({ calendar_events: event.target.value })} placeholder="Например: 1.1–1.4, 2.1–2.3, 3.1" />
        </FieldBlock>
      </div>
    </article>
  );
}

function SalaryResultBlock({ result, onRerun }: { result: SalaryGenerateResult; onRerun: () => void }) {
  const docx = result.downloads.docx;

  async function copyText() {
    await navigator.clipboard?.writeText(result.plain_text);
  }

  return (
    <section className="rounded-3xl border border-green-200 bg-green-50 p-6 text-green-950">
      <p className="text-sm font-semibold uppercase tracking-wide">Расчет готов</p>
      <h3 className="mt-2 text-3xl font-bold">Plain-text результат</h3>
      <pre className="mt-5 max-h-[560px] overflow-auto whitespace-pre-wrap rounded-2xl bg-white p-5 text-base leading-7 text-slate-800">{result.plain_text}</pre>
      {result.warnings?.length ? (
        <div className="mt-4 rounded-2xl bg-orange-50 p-4 text-base leading-7 text-orange-950">
          {result.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-3">
        {docx ? (
          <a href={apiUrl(docx)} className="inline-flex min-h-14 items-center justify-center rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white hover:bg-blue-900">
            Скачать DOCX
          </a>
        ) : null}
        <button type="button" onClick={() => void copyText()} className="min-h-14 rounded-2xl border border-green-700 bg-white px-6 py-4 text-lg font-semibold text-green-900 hover:bg-green-100">
          Скопировать текст
        </button>
        <button type="button" onClick={onRerun} className="min-h-14 rounded-2xl border border-green-700 bg-white px-6 py-4 text-lg font-semibold text-green-900 hover:bg-green-100">
          Рассчитать заново
        </button>
        <a href={`/run/${result.run_id}/result`} className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-green-700 bg-white px-6 py-4 text-lg font-semibold text-green-900 hover:bg-green-100">
          Открыть страницу результата
        </a>
      </div>
    </section>
  );
}

function FieldBlock({ label, hint, required = false, children }: { label: string; hint: string; required?: boolean; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-bold text-slate-950">{label}</span>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${required ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
          {required ? "обязательно" : "можно позже"}
        </span>
      </span>
      <span className="mt-2 block text-base leading-7 text-slate-600">{hint}</span>
      <span className="mt-4 block">{children}</span>
    </label>
  );
}

function InlineError({ children }: { children: React.ReactNode }) {
  return <span className="mt-2 block rounded-xl bg-red-50 px-3 py-2 text-base text-red-900">{children}</span>;
}

function validateDraft(draft: SalaryDraft) {
  const errors: string[] = [];
  if (!draft.region.trim()) errors.push("Выберите регион расчета.");
  if (!draft.cofinance_source) errors.push("Выберите источник софинансирования.");
  if (!draft.positions.length) errors.push("Добавьте хотя бы одну должность.");

  draft.positions.forEach((position) => {
    if (!position.role_title.trim()) errors.push("Укажите должность в проекте.");
    if (toNumber(position.staff_count) < 1) errors.push("Количество сотрудников должно быть не меньше 1.");
    if (toNumber(position.duration_months) <= 0) errors.push("Укажите срок работы в месяцах.");
    if (position.workload_mode === "percent" && (toNumber(position.workload_value) <= 0 || toNumber(position.workload_value) > 100)) {
      errors.push("Процент занятости должен быть от 1 до 100.");
    }
    if (position.workload_mode === "hours_total" && toNumber(position.workload_value) <= 0) {
      errors.push("Укажите количество часов за весь проект.");
    }
  });

  return Array.from(new Set(errors));
}

function toApiPayload(draft: SalaryDraft) {
  return {
    region: draft.region.trim(),
    source_scope: draft.source_scope,
    cofinance_source: draft.cofinance_source,
    positions: draft.positions.map((position) => ({
      role_title: position.role_title.trim(),
      staff_count: toNumber(position.staff_count),
      duration_months: toNumber(position.duration_months),
      workload_mode: position.workload_mode,
      workload_value: toNumber(position.workload_value),
      functionality: position.functionality.trim(),
      calendar_events: position.calendar_events.trim(),
    })),
  };
}

function normalizeDraft(source: Partial<SalaryDraft>): SalaryDraft {
  const positions = Array.isArray(source.positions) && source.positions.length ? source.positions.map(normalizePosition) : [defaultPosition()];
  return {
    region: typeof source.region === "string" ? source.region : "",
    source_scope: source.source_scope === "aggregators" || source.source_scope === "official" ? source.source_scope : "all",
    cofinance_source: source.cofinance_source === "own_legal_entity_funds" || source.cofinance_source === "partner_letter_funds" ? source.cofinance_source : "",
    positions,
  };
}

function normalizePosition(source: Partial<SalaryPositionDraft>): SalaryPositionDraft {
  return {
    id: source.id || draftId(),
    role_title: source.role_title || "",
    staff_count: source.staff_count || "1",
    duration_months: source.duration_months || "4",
    workload_mode: source.workload_mode === "hours_total" ? "hours_total" : "percent",
    workload_value: source.workload_value || "",
    functionality: source.functionality || "",
    calendar_events: source.calendar_events || "",
  };
}

function defaultDraft(): SalaryDraft {
  return {
    region: "",
    source_scope: "all",
    cofinance_source: "",
    positions: [defaultPosition()],
  };
}

function loadInitialDraft(): SalaryDraft {
  if (typeof window === "undefined") return defaultDraft();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? normalizeDraft(JSON.parse(raw)) : defaultDraft();
  } catch {
    return defaultDraft();
  }
}

function defaultPosition(): SalaryPositionDraft {
  return {
    id: draftId(),
    role_title: "",
    staff_count: "1",
    duration_months: "4",
    workload_mode: "percent",
    workload_value: "",
    functionality: "",
    calendar_events: "",
  };
}

function salaryButtonLabel(usage: UsagePayload | null) {
  const freeAvailable = usage?.modules?.salary?.free_attempt_available ?? true;
  if (freeAvailable || (usage?.paid_runs ?? 0) > 0) return "Рассчитать зарплату";
  return "Купить запуск модуля";
}

function toNumber(value: string) {
  const parsed = Number(String(value || "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function draftId() {
  return `pos-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
}

const inputClassName = "min-h-14 w-full rounded-2xl border border-slate-300 bg-white p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100";
