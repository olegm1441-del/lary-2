"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { LaryModule } from "../lib/lary-data";
import { apiUrl, readApiError } from "../lib/api-client";
import { USAGE_UPDATED_EVENT } from "./module-attempt-status";
import { migrateLegacyDraft, moduleDraftKey } from "../lib/module-drafts";
import { emitModuleResultReady } from "../lib/module-flow";

type UsagePayload = {
  paid_runs: number;
  modules: Record<string, { free_attempt_available: boolean; free_attempt_used: boolean }>;
};

type WorkloadMode = "percent" | "hours_total";
type CofinanceSource = "own_legal_entity_funds" | "partner_letter_funds";
type VoiceState = "idle" | "recording" | "uploading";

type SalaryPositionDraft = {
  id: string;
  role_title: string;
  staff_count: string;
  duration_months: string;
  workload_mode: WorkloadMode;
  workload_value: string;
  functionality: string;
  calendar_events: string;
  cofinance_source: CofinanceSource | "";
};

type SalaryDraft = {
  region: string;
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

const REGION_OPTIONS = ["Свердловская область", "Республика Татарстан", "Москва", "Санкт-Петербург", "Краснодарский край", "Нижегородская область"];
const COFINANCE_OPTIONS: Array<{ value: CofinanceSource; label: string }> = [
  { value: "own_legal_entity_funds", label: "Собственные средства юридического лица" },
  { value: "partner_letter_funds", label: "Привлеченные средства согласно письму поддержки" },
];

export function SalaryModuleRunner({ module, contestSlug, profileVersion, projectId }: { module: LaryModule; contestSlug: string; profileVersion?: string | null; projectId?: string | null }) {
  const [draft, setDraft] = useState<SalaryDraft>(() => defaultDraft());
  const [usage, setUsage] = useState<UsagePayload | null>(null);
  const [state, setState] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<SalaryGenerateResult | null>(null);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceTargetId, setVoiceTargetId] = useState<string | null>(null);
  const [voiceMessage, setVoiceMessage] = useState("");
  const [refinementOpen, setRefinementOpen] = useState(false);
  const [refinementInstruction, setRefinementInstruction] = useState("");
  const [refinementError, setRefinementError] = useState("");

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const sourceSampleRateRef = useRef(44100);
  const stopTimerRef = useRef<number | null>(null);

  const validationErrors = useMemo(() => validateDraft(draft), [draft]);
  const canSubmit = validationErrors.length === 0;
  const duplicateTitleCounts = useMemo(() => buildDuplicateTitleCounts(draft.positions), [draft.positions]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const migrated = migrateLegacyDraft<SalaryDraft>(window.localStorage, "salary", contestSlug, projectId);
        const raw = window.localStorage.getItem(moduleDraftKey("salary", contestSlug, projectId));
        setDraft(normalizeDraft(raw ? JSON.parse(raw) : migrated || defaultDraft()));
      } catch {
        setDraft(defaultDraft());
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [contestSlug, projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(moduleDraftKey("salary", contestSlug, projectId), JSON.stringify(draft));
      } catch {
        // Локальный черновик не является источником истины.
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [contestSlug, draft, projectId]);

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

  async function submit(event?: FormEvent<HTMLFormElement>, draftOverride?: SalaryDraft) {
    event?.preventDefault();
    setMessage("");

    const activeDraft = draftOverride || draft;
    const errors = validateDraft(activeDraft);
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
        body: JSON.stringify({
          ...toApiPayload(activeDraft),
          contest_slug: contestSlug,
          profile_version: profileVersion,
          project_id: projectId,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setResult(payload);
      emitModuleResultReady("salary", "result");
      setState("idle");
      setMessage("");
      window.dispatchEvent(new CustomEvent(USAGE_UPDATED_EVENT));
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Не удалось найти подтвержденные данные по этой должности в выбранном регионе. Черновик сохранен. Уточните название должности и повторите расчет.");
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

  function appendPositionText(id: string, text: string) {
    setDraft((current) => ({
      ...current,
      positions: current.positions.map((position) => (position.id === id ? { ...position, functionality: appendText(position.functionality, text) } : position)),
    }));
  }

  async function submitFunctionalityRefinement() {
    const instruction = refinementInstruction.trim();
    if (!instruction) {
      setRefinementError("Напишите, что нужно изменить в функционале сотрудника.");
      return;
    }

    const nextDraft = {
      ...draft,
      positions: draft.positions.map((position) => ({
        ...position,
        functionality: appendText(position.functionality, `Пожелание к доработке функционала сотрудника: ${instruction}`),
      })),
    };
    setDraft(nextDraft);
    setRefinementOpen(false);
    setRefinementInstruction("");
    setRefinementError("");
    await submit(undefined, nextDraft);
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

  async function startVoice(positionId: string) {
    if (voiceState === "recording" && voiceTargetId === positionId) {
      await stopVoiceAndSend();
      return;
    }
    if (voiceState !== "idle") {
      setVoiceMessage("Сначала завершите текущую голосовую запись.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceMessage("В этом браузере голосовой ввод недоступен. Заполните поле текстом.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextClass = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) {
        stream.getTracks().forEach((track) => track.stop());
        setVoiceMessage("Браузер не поддерживает запись звука. Заполните поле текстом.");
        return;
      }

      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      const silentGain = audioContext.createGain();
      silentGain.gain.value = 0;

      audioChunksRef.current = [];
      sourceSampleRateRef.current = audioContext.sampleRate;
      processor.onaudioprocess = (event) => {
        audioChunksRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioContext.destination);

      mediaStreamRef.current = stream;
      audioContextRef.current = audioContext;
      processorRef.current = processor;
      sourceRef.current = source;
      silentGainRef.current = silentGain;
      setVoiceTargetId(positionId);
      setVoiceState("recording");
      setVoiceMessage("Идет запись поля «Что делает сотрудник». Нажмите «Остановить запись», когда закончите.");
      stopTimerRef.current = window.setTimeout(() => {
        void stopVoiceAndSend();
      }, 55_000);
    } catch {
      setVoiceState("idle");
      setVoiceTargetId(null);
      setVoiceMessage("Не удалось получить доступ к микрофону. Проверьте разрешение браузера или заполните поле текстом.");
      cleanupVoice();
    }
  }

  async function stopVoiceAndSend() {
    const targetId = voiceTargetId;
    if (!targetId) return;

    setVoiceState("uploading");
    setVoiceMessage("Распознаем запись для поля «Что делает сотрудник»...");
    cleanupVoice();

    const chunks = audioChunksRef.current;
    if (!chunks.length) {
      setVoiceState("idle");
      setVoiceTargetId(null);
      setVoiceMessage("Запись получилась пустой. Попробуйте еще раз или заполните поле текстом.");
      return;
    }

    try {
      const pcm = encodePcm16(downsampleTo16Khz(chunks, sourceSampleRateRef.current));
      const formData = new FormData();
      formData.append("audio", new File([pcm], "voice.pcm", { type: "audio/x-pcm;bit=16;rate=16000" }));
      const response = await fetch(apiUrl("/api/speech/transcribe"), {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      const text = typeof payload?.text === "string" ? payload.text.trim() : "";
      if (!text) throw new Error("Не получилось распознать голос. Можно заполнить поле текстом.");
      appendPositionText(targetId, text);
      setVoiceMessage("");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "Не получилось распознать голос. Можно заполнить поле текстом.");
    } finally {
      setVoiceState("idle");
      setVoiceTargetId(null);
      audioChunksRef.current = [];
    }
  }

  function cleanupVoice() {
    if (stopTimerRef.current) {
      window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    silentGainRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();
    processorRef.current = null;
    sourceRef.current = null;
    silentGainRef.current = null;
    mediaStreamRef.current = null;
    audioContextRef.current = null;
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="mt-6 grid gap-5">
      <section className="rounded-3xl border border-slate-200 bg-white p-5">
        <div className="grid gap-5">
          <FieldBlock label="Регион" required>
            <input
              list="salary-region-options"
              value={draft.region}
              onChange={(event) => updateDraft("region", event.target.value)}
              className={inputClassName}
              placeholder="Например: Санкт-Петербург"
            />
            <datalist id="salary-region-options">
              {REGION_OPTIONS.map((region) => (
                <option key={region} value={region} />
              ))}
            </datalist>
            {!draft.region.trim() ? <InlineError>Выберите регион расчета.</InlineError> : null}
          </FieldBlock>

        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5">
        <h3 className="text-2xl font-bold text-slate-950">Позиции расчета</h3>
        <div className="mt-5 grid gap-5">
          {draft.positions.map((position, index) => (
            <PositionCard
              key={position.id}
              title={positionDisplayTitle(position, duplicateTitleCounts, draft.positions.slice(0, index + 1))}
              position={position}
              canDelete={draft.positions.length > 1}
              onChange={(patch) => updatePosition(position.id, patch)}
              onDuplicate={() => duplicatePosition(position.id)}
              onRemove={() => removePosition(position.id)}
              onStartVoice={() => void startVoice(position.id)}
              voiceState={voiceTargetId === position.id ? voiceState : "idle"}
            />
          ))}
          <button type="button" onClick={addPosition} className="min-h-12 rounded-2xl border border-blue-800 px-5 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50">
            Добавить должность
          </button>
        </div>
      </section>

      {voiceMessage ? <div className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">{voiceMessage}</div> : null}

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

      {result ? <SalaryResultBlock result={result} onOpenRefinement={() => setRefinementOpen(true)} /> : null}
      {refinementOpen ? (
        <FunctionalityRefinementDialog
          value={refinementInstruction}
          error={refinementError}
          submitting={state === "submitting"}
          onChange={(value) => {
            setRefinementInstruction(value);
            setRefinementError("");
          }}
          onCancel={() => {
            setRefinementOpen(false);
            setRefinementError("");
          }}
          onSubmit={() => void submitFunctionalityRefinement()}
        />
      ) : null}
      <p className="sr-only">{module.shortTitle}</p>
    </form>
  );
}

function PositionCard({
  title,
  position,
  canDelete,
  onChange,
  onDuplicate,
  onRemove,
  onStartVoice,
  voiceState,
}: {
  title: string;
  position: SalaryPositionDraft;
  canDelete: boolean;
  onChange: (patch: Partial<SalaryPositionDraft>) => void;
  onDuplicate: () => void;
  onRemove: () => void;
  onStartVoice: () => void;
  voiceState: VoiceState;
}) {
  const workloadLabel = position.workload_mode === "hours_total" ? "Часы за весь проект на одного сотрудника" : "Занятость одного сотрудника, %";
  const workloadHint =
    position.workload_mode === "hours_total"
      ? "Формула: зарплата / 166 × часы × количество."
      : "Формула: зарплата × процент × месяцы × количество.";

  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-xl font-bold text-slate-950">{title}</h4>
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
        <FieldBlock label="Должность в проекте" required hint="Как в бюджете проекта.">
          <input className={inputClassName} value={position.role_title} onChange={(event) => onChange({ role_title: event.target.value })} placeholder="Например: координатор проекта" />
        </FieldBlock>

        <div className="grid gap-5 sm:grid-cols-2">
          <FieldBlock label="Количество сотрудников в этой роли" required>
            <input className={inputClassName} inputMode="numeric" pattern="[0-9]*" value={position.staff_count} onChange={(event) => onChange({ staff_count: event.target.value })} placeholder="Например: 1" />
          </FieldBlock>
          <FieldBlock label="Срок работы в проекте, месяцев" required>
            <input className={inputClassName} inputMode="decimal" value={position.duration_months} onChange={(event) => onChange({ duration_months: event.target.value })} placeholder="Например: 4" />
          </FieldBlock>
        </div>

        <FieldBlock label="Как считать занятость" required>
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
          <input
            className={inputClassName}
            inputMode="decimal"
            value={position.workload_value}
            onChange={(event) => onChange({ workload_value: event.target.value })}
            placeholder={position.workload_mode === "percent" ? "Например: 40" : "Например: 96"}
          />
        </FieldBlock>

        <FieldBlock label="Что делает сотрудник" hint="Можно оставить пустым — Лари предложит типовой функционал по должности.">
          <textarea className={`${inputClassName} min-h-32`} value={position.functionality} onChange={(event) => onChange({ functionality: event.target.value })} placeholder="Например: ведет списки участников, согласует расписание, собирает обратную связь" />
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onStartVoice}
              disabled={voiceState === "uploading"}
              className="min-h-12 rounded-2xl border border-blue-800 px-4 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50 disabled:border-slate-300 disabled:text-slate-400"
            >
              {voiceState === "recording" ? "Остановить запись" : voiceState === "uploading" ? "Распознаем..." : "Наговорить ответ"}
            </button>
            {position.functionality ? (
              <button
                type="button"
                onClick={() => onChange({ functionality: "" })}
                className="min-h-12 rounded-2xl border border-slate-300 px-4 py-3 text-base font-semibold text-slate-700 hover:bg-slate-50"
              >
                Очистить
              </button>
            ) : null}
          </div>
        </FieldBlock>

        <FieldBlock label="Мероприятия календарного плана" hint="Если неизвестно, оставьте пустым.">
          <input className={inputClassName} value={position.calendar_events} onChange={(event) => onChange({ calendar_events: event.target.value })} placeholder="Например: 1.1–1.4, 2.1–2.3, 3.1" />
        </FieldBlock>

        <FieldBlock label="Софинансирование" required>
          <div className="grid gap-3 sm:grid-cols-2">
            {COFINANCE_OPTIONS.map((option) => (
              <label key={option.value} className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border p-4 ${position.cofinance_source === option.value ? "border-blue-800 bg-blue-50" : "border-slate-300 bg-white"}`}>
                <input
                  type="radio"
                  name={`cofinance_source-${position.id}`}
                  value={option.value}
                  checked={position.cofinance_source === option.value}
                  onChange={(event) => onChange({ cofinance_source: event.target.value as CofinanceSource })}
                />
                <span className="font-semibold">{option.label}</span>
              </label>
            ))}
          </div>
          {!position.cofinance_source ? <InlineError>Выберите источник софинансирования для этой должности.</InlineError> : null}
        </FieldBlock>
      </div>
    </article>
  );
}

function SalaryResultBlock({ result, onOpenRefinement }: { result: SalaryGenerateResult; onOpenRefinement: () => void }) {
  const docx = result.downloads.docx;
  const [copied, setCopied] = useState(false);

  async function copyText() {
    await navigator.clipboard?.writeText(result.plain_text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section id="result" className="min-w-0 rounded-3xl border border-green-200 bg-green-50 p-6 text-green-950">
      <h3 className="text-3xl font-bold">Расчет готов</h3>
      <div className="mt-5 flex flex-wrap gap-3">
        {docx ? (
          <a href={apiUrl(docx)} className="inline-flex min-h-14 items-center justify-center rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white hover:bg-blue-900">
            Скачать DOCX
          </a>
        ) : null}
        <button type="button" onClick={() => void copyText()} className="min-h-14 rounded-2xl border border-green-700 bg-white px-6 py-4 text-lg font-semibold text-green-900 hover:bg-green-100">
          ⧉ Скопировать
        </button>
        <button type="button" onClick={onOpenRefinement} className="min-h-14 rounded-2xl border border-green-700 bg-white px-6 py-4 text-lg font-semibold text-green-900 hover:bg-green-100">
          Рассчитать заново
        </button>
      </div>
      {copied ? <p className="mt-3 rounded-2xl bg-white px-4 py-3 text-base font-semibold text-green-900">Скопировано</p> : null}
      <h4 className="mt-6 text-2xl font-bold">Текст результата</h4>
      <pre className="mt-4 max-h-[560px] max-w-full overflow-auto whitespace-pre-wrap break-words rounded-2xl bg-white p-5 text-base leading-7 text-slate-800 [overflow-wrap:anywhere]">{result.plain_text}</pre>
      {result.warnings?.length ? (
        <div className="mt-4 rounded-2xl bg-orange-50 p-4 text-base leading-7 text-orange-950">
          {result.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function FunctionalityRefinementDialog({
  value,
  error,
  submitting,
  onChange,
  onCancel,
  onSubmit,
}: {
  value: string;
  error: string;
  submitting: boolean;
  onChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end bg-slate-950/40 p-4 sm:items-center sm:justify-center" role="dialog" aria-modal="true" aria-labelledby="salary-refinement-title">
      <div className="w-full max-w-xl rounded-3xl bg-white p-5 shadow-2xl">
        <h3 id="salary-refinement-title" className="text-2xl font-bold text-slate-950">
          что именно изменить в функционале сотрудника?
        </h3>
        <p className="mt-3 text-base leading-7 text-slate-600">Напишите коротко, что добавить, убрать или уточнить. Лари пересчитает результат и перепишет абзац официальным языком.</p>
        <textarea
          className={`${inputClassName} mt-4 min-h-36`}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Например: сделать акцент на уборке площадки после мероприятий и подготовке зала до прихода участников"
        />
        {error ? <p className="mt-3 rounded-2xl bg-red-50 px-4 py-3 text-base text-red-900">{error}</p> : null}
        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" onClick={onSubmit} disabled={submitting} className="min-h-12 rounded-2xl bg-blue-800 px-5 py-3 text-base font-semibold text-white hover:bg-blue-900 disabled:cursor-wait disabled:bg-slate-400">
            Применить и рассчитать заново
          </button>
          <button type="button" onClick={onCancel} disabled={submitting} className="min-h-12 rounded-2xl border border-slate-300 px-5 py-3 text-base font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-wait">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}

function FieldBlock({ label, hint, required = false, children }: { label: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-bold text-slate-950">{label}</span>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${required ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
          {required ? "обязательно" : "можно позже"}
        </span>
      </span>
      {hint ? <span className="mt-2 block text-base leading-7 text-slate-600">{hint}</span> : null}
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
  if (!draft.positions.length) errors.push("Добавьте хотя бы одну должность.");

  draft.positions.forEach((position) => {
    if (!position.cofinance_source) errors.push("Выберите источник софинансирования для каждой должности.");
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
    positions: draft.positions.map((position) => ({
      role_title: position.role_title.trim(),
      staff_count: toNumber(position.staff_count),
      duration_months: toNumber(position.duration_months),
      workload_mode: position.workload_mode,
      workload_value: toNumber(position.workload_value),
      functionality: position.functionality.trim(),
      calendar_events: position.calendar_events.trim(),
      cofinance_source: position.cofinance_source,
    })),
  };
}

function normalizeDraft(source: Partial<SalaryDraft>): SalaryDraft {
  const legacyCofinance = (source as Partial<SalaryDraft> & { cofinance_source?: string }).cofinance_source;
  const positions = Array.isArray(source.positions) && source.positions.length ? source.positions.map((position) => normalizePosition(position, legacyCofinance)) : [defaultPosition()];
  return {
    region: typeof source.region === "string" ? source.region : "",
    positions,
  };
}

function normalizePosition(source: Partial<SalaryPositionDraft>, legacyCofinance?: string): SalaryPositionDraft {
  const cofinance_source = source.cofinance_source || legacyCofinance;
  return {
    id: source.id || draftId(),
    role_title: source.role_title || "",
    staff_count: source.staff_count || "1",
    duration_months: source.duration_months || "4",
    workload_mode: source.workload_mode === "hours_total" ? "hours_total" : "percent",
    workload_value: source.workload_value || "",
    functionality: source.functionality || "",
    calendar_events: source.calendar_events || "",
    cofinance_source: cofinance_source === "own_legal_entity_funds" || cofinance_source === "partner_letter_funds" ? cofinance_source : "",
  };
}

function defaultDraft(): SalaryDraft {
  return {
    region: "",
    positions: [defaultPosition()],
  };
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
    cofinance_source: "",
  };
}

function positionDisplayTitle(position: SalaryPositionDraft, duplicateTitleCounts: Record<string, number>, previousPositions: SalaryPositionDraft[]) {
  const base = titleizeRole(position.role_title);
  if (!base) return "Новая должность";
  const key = titleKey(position.role_title);
  if ((duplicateTitleCounts[key] || 0) < 2) return base;
  const index = previousPositions.filter((item) => titleKey(item.role_title) === key).length;
  return `${base} ${index}`;
}

function buildDuplicateTitleCounts(positions: SalaryPositionDraft[]) {
  const duplicateTitleCounts: Record<string, number> = {};
  positions.forEach((position) => {
    const key = titleKey(position.role_title);
    if (!key) return;
    duplicateTitleCounts[key] = (duplicateTitleCounts[key] || 0) + 1;
  });
  return duplicateTitleCounts;
}

function titleizeRole(value: string) {
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (!cleaned) return "";
  return `${cleaned[0].toUpperCase()}${cleaned.slice(1)}`;
}

function titleKey(value: string) {
  return value.trim().toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ");
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

function appendText(current: string | undefined, addition: string) {
  const base = String(current || "").trim();
  return base ? `${base}\n${addition}` : addition;
}

function downsampleTo16Khz(chunks: Float32Array[], inputSampleRate: number) {
  const inputLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const input = new Float32Array(inputLength);
  let offset = 0;
  for (const chunk of chunks) {
    input.set(chunk, offset);
    offset += chunk.length;
  }

  const targetSampleRate = 16000;
  if (inputSampleRate === targetSampleRate) return input;
  const ratio = inputSampleRate / targetSampleRate;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outputLength);
  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(Math.floor((index + 1) * ratio), input.length);
    let total = 0;
    let count = 0;
    for (let sourceIndex = start; sourceIndex < end; sourceIndex += 1) {
      total += input[sourceIndex];
      count += 1;
    }
    output[index] = count ? total / count : 0;
  }
  return output;
}

function encodePcm16(samples: Float32Array) {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return buffer;
}

const inputClassName = "min-h-14 w-full rounded-2xl border border-slate-300 bg-white p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100";
