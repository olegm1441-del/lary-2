"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getFieldKey, getFieldOptions, type LaryModule, type ModuleField } from "../lib/lary-data";
import { apiUrl, readApiError } from "../lib/api-client";
import {
  FieldAssistantHint,
  type FieldAssistantHintData,
  type FieldAssistantSuggestion,
} from "./field-assistant-hint";
import { USAGE_UPDATED_EVENT } from "./module-attempt-status";
import { SalaryModuleRunner } from "./salary-module-runner";
import { migrateLegacyDraft, moduleDraftKey, moduleResultStateKey } from "../lib/module-drafts";
import { emitModuleResultReady } from "../lib/module-flow";
import { ResultViewer } from "./result-viewer";
import { stableSubmissionFingerprint } from "../lib/submission-fingerprint";

type RunState = "idle" | "submitting" | "error";
type VoiceState = "idle" | "recording" | "uploading";
type VoiceTarget = { key: string; label: string };
type UsagePayload = {
  paid_runs: number;
  modules: Record<string, { free_attempt_available: boolean; free_attempt_used: boolean }>;
};

type FieldHintMap = Record<string, FieldAssistantHintData>;

export function ModuleRunner({
  module,
  contestSlug,
  profileVersion,
  projectId,
}: {
  module: LaryModule;
  contestSlug: string;
  profileVersion?: string | null;
  projectId?: string | null;
}) {
  if (module.slug === "salary") return <SalaryModuleRunner module={module} contestSlug={contestSlug} profileVersion={profileVersion} projectId={projectId} />;

  return <GenericModuleRunner module={module} contestSlug={contestSlug} profileVersion={profileVersion} projectId={projectId} />;
}

function GenericModuleRunner({ module, contestSlug, profileVersion, projectId }: { module: LaryModule; contestSlug: string; profileVersion?: string | null; projectId?: string | null }) {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, string>>({});
  const [state, setState] = useState<RunState>("idle");
  const [message, setMessage] = useState("");
  const [voiceMessage, setVoiceMessage] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceTarget, setVoiceTarget] = useState<VoiceTarget | null>(null);
  const [fieldHints, setFieldHints] = useState<FieldHintMap>({});
  const [touchedFields, setTouchedFields] = useState<Record<string, boolean>>({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [scenarioHelper, setScenarioHelper] = useState("");
  const [usage, setUsage] = useState<UsagePayload | null>(null);
  const [resultRunId, setResultRunId] = useState<string | null>(null);
  const [lastSubmittedPayload, setLastSubmittedPayload] = useState<Record<string, unknown> | null>(null);
  const [lastSubmittedFingerprint, setLastSubmittedFingerprint] = useState<string | null>(null);
  const [lastCompletedRunId, setLastCompletedRunId] = useState<string | null>(null);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const sourceSampleRateRef = useRef(44100);
  const stopTimerRef = useRef<number | null>(null);
  const loadedDraftKeyRef = useRef<string | null>(null);

  const presentationVariant = useMemo(() => {
    if (module.slug !== "presentation") return undefined;
    return values.presentation_variant || "grant_defense";
  }, [module.slug, values.presentation_variant]);

  const visibleFieldKeys = useMemo(
    () => module.fields.map((field, fieldIndex) => getFieldKey(module.slug, fieldIndex, field.label)),
    [module.fields, module.slug],
  );
  const currentSubmissionPayload = useMemo(
    () => ({
      module_slug: module.slug,
      contest_slug: contestSlug,
      profile_version: profileVersion || null,
      project_id: projectId || null,
      inputs: buildSubmissionInputs(module.slug, applyModuleDefaults(module.slug, values)),
      presentation_variant: presentationVariant || null,
    }),
    [contestSlug, module.slug, presentationVariant, profileVersion, projectId, values],
  );
  const currentFingerprint = useMemo(
    () => stableSubmissionFingerprint(currentSubmissionPayload),
    [currentSubmissionPayload],
  );
  const resultMatchesCurrent = Boolean(resultRunId && lastSubmittedFingerprint === currentFingerprint);
  const resultIsOutdated = Boolean(resultRunId && lastSubmittedFingerprint && lastSubmittedFingerprint !== currentFingerprint);

  const collectFieldHints = useCallback(
    (force: boolean, currentValues = values): FieldHintMap => {
      const nextHints: FieldHintMap = {};
      module.fields.forEach((field, fieldIndex) => {
        const key = getFieldKey(module.slug, fieldIndex, field.label);
        const value = String(currentValues[key] || "");
        const shouldShowLegalRegion = module.slug === "legal-acts" && key === "region" && isRegionalLegalSearch(currentValues.program_level);
        const shouldShow = force || submitAttempted || touchedFields[key] || value.trim().length > 0 || shouldShowLegalRegion;
        if (!shouldShow) return;
        const hint = getFieldQualityHint(module.slug, key, field, value, currentValues, force || submitAttempted || Boolean(touchedFields[key]) || shouldShowLegalRegion);
        if (hint.status !== "success") nextHints[key] = hint;
      });
      return nextHints;
    },
    [module.fields, module.slug, submitAttempted, touchedFields, values],
  );

  useEffect(() => {
    loadedDraftKeyRef.current = null;
    const timer = window.setTimeout(() => {
      const key = moduleDraftKey(module.slug, contestSlug, projectId);
      try {
        const raw = window.localStorage.getItem(key);
        const draft = raw ? JSON.parse(raw) : migrateLegacyDraft<Record<string, string>>(window.localStorage, module.slug, contestSlug, projectId) || {};
        setValues(applyModuleDefaults(module.slug, draft));
        const savedResultRaw = window.localStorage.getItem(moduleResultStateKey(module.slug, contestSlug, projectId));
        const savedResult = savedResultRaw ? JSON.parse(savedResultRaw) : null;
        if (savedResult?.runId && savedResult?.fingerprint) {
          setResultRunId(String(savedResult.runId));
          setLastCompletedRunId(String(savedResult.runId));
          setLastSubmittedFingerprint(String(savedResult.fingerprint));
          setLastSubmittedPayload(savedResult.payload && typeof savedResult.payload === "object" ? savedResult.payload : null);
        } else {
          setResultRunId(null);
          setLastSubmittedPayload(null);
          setLastSubmittedFingerprint(null);
          setLastCompletedRunId(null);
        }
      } catch {
        setValues(applyModuleDefaults(module.slug, {}));
        setResultRunId(null);
        setLastSubmittedPayload(null);
        setLastSubmittedFingerprint(null);
        setLastCompletedRunId(null);
      }
      loadedDraftKeyRef.current = key;
      setTouchedFields({});
      setFieldHints({});
      setSubmitAttempted(false);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [contestSlug, module.slug, projectId]);

  useEffect(() => {
    const key = moduleDraftKey(module.slug, contestSlug, projectId);
    if (loadedDraftKeyRef.current !== key) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(values));
    } catch {
      // Draft persistence is a convenience only. Backend state remains authoritative.
    }
  }, [contestSlug, module.slug, projectId, values]);

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
  }, [module.slug]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      const nextHints = collectFieldHints(false);
      const aiCandidate = module.fields
        .map((field, fieldIndex) => ({ field, key: getFieldKey(module.slug, fieldIndex, field.label) }))
        .find(({ key }) => {
          const value = String(values[key] || "").trim();
          return !nextHints[key] && touchedFields[key] && ["constraints", "team_equipment_constraints", "project_description", "event_idea", "problem"].includes(key) && value.length > 80;
        });

      if (aiCandidate) {
        const aiHint = await requestAiFieldAssistant(module.slug, aiCandidate.key, aiCandidate.field.label, values[aiCandidate.key], values);
        if (!cancelled && aiHint && aiHint.status !== "success") nextHints[aiCandidate.key] = aiHint;
      }

      if (!cancelled) setFieldHints(nextHints);
    }, 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [module.slug, module.fields, values, touchedFields, collectFieldHints]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (resultMatchesCurrent || state === "submitting") return;
    setSubmitAttempted(true);

    const nextValues = applyModuleDefaults(module.slug, values);
    const nextHints = collectFieldHints(true, nextValues);
    setValues(nextValues);
    setFieldHints(nextHints);

    if (Object.values(nextHints).some((hint) => hint.should_block)) {
      setState("error");
      setMessage(module.slug === "support-letter" ? "Заполните обязательные поля, чтобы запустить" : "Исправьте поля с красной подсказкой.");
      return;
    }

    const freeAvailable = usage?.modules?.[module.slug]?.free_attempt_available ?? true;
    const paidRuns = usage?.paid_runs ?? 0;
    if (!freeAvailable && paidRuns <= 0) {
      if (resultIsOutdated) {
        router.push(`/pay?return=${encodeURIComponent(`/m/${module.slug}?contest=${contestSlug}&mode=start${projectId ? `&project_id=${projectId}` : ""}#data`)}`);
        return;
      }
      setState("error");
      setMessage("Для повторного запуска необходимо купить запуск модуля или применить промокод.");
      return;
    }

    setState("submitting");
    setMessage(module.slug === "support-letter" ? "Готовим письмо поддержки..." : "Лари готовит результат. Данные сохранены.");
    const submissionInputs = buildSubmissionInputs(module.slug, nextValues);

    try {
      const response = await fetch(apiUrl("/api/module-runs"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module_slug: module.slug,
          contest_slug: contestSlug,
          profile_version: profileVersion,
          project_id: projectId,
          inputs: submissionInputs,
          presentation_variant: presentationVariant,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const payload = await response.json();
      setResultRunId(payload.run_id);
      setLastCompletedRunId(payload.run_id);
      setLastSubmittedPayload(currentSubmissionPayload);
      const completedFingerprint = stableSubmissionFingerprint(currentSubmissionPayload);
      setLastSubmittedFingerprint(completedFingerprint);
      try {
        window.localStorage.setItem(
          moduleResultStateKey(module.slug, contestSlug, projectId),
          JSON.stringify({
            runId: payload.run_id,
            fingerprint: completedFingerprint,
            payload: currentSubmissionPayload,
          }),
        );
      } catch {
        // The completed backend run remains available even if local convenience state cannot be stored.
      }
      setState("idle");
      setMessage("");
      window.dispatchEvent(new CustomEvent(USAGE_UPDATED_EVENT));
      emitModuleResultReady(module.slug, "result");
    } catch (error) {
      setState("error");
      setMessage(
        error instanceof Error
          ? error.message
          : module.slug === "support-letter"
            ? "Не получилось подготовить письмо. Данные сохранены. Попробуйте еще раз через минуту."
            : "Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту.",
      );
    }
  }

  function updateValue(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
    setTouchedFields((current) => ({ ...current, [key]: true }));
    if (key === "scenario_type" && value !== "Не знаю — помогите выбрать") setScenarioHelper("");
  }

  function markTouched(key: string) {
    setTouchedFields((current) => ({ ...current, [key]: true }));
  }

  function appendValue(key: string, value: string) {
    setValues((current) => ({
      ...current,
      [key]: current[key] ? `${current[key]}\n${value}` : value,
    }));
    setTouchedFields((current) => ({ ...current, [key]: true }));
  }

  function toggleMultiValue(key: string, option: string) {
    const selected = selectedMultiValues(values[key]);
    const next = selected.includes(option) ? selected.filter((item) => item !== option) : [...selected, option];
    updateValue(key, next.join("; "));
  }

  function fillUnknownField(key: string) {
    if (key === "scenario_type") {
      updateValue(key, "Не знаю — помогите выбрать");
      setScenarioHelper("Лари выберет базовую структуру по описанию идеи. Если знаете формат события, лучше выбрать его вручную.");
      return;
    }

    setFieldHints((current) => ({
      ...current,
      [key]: {
        status: "info",
        should_block: false,
        message: "Можно оставить пустым. Лари отметит место для ручной вставки, если это важно для результата.",
        suggestions: [{ id: "leave_empty", label: "Оставить пустым", operation: "dismiss", text: "" }],
        covered_by_fields: [],
      },
    }));
  }

  function applyHintSuggestion(key: string, suggestion: FieldAssistantSuggestion) {
    if (suggestion.operation === "dismiss") {
      setFieldHints((current) => {
        const copy = { ...current };
        delete copy[key];
        return copy;
      });
      return;
    }
    if (suggestion.operation === "suggest_text" && suggestion.text) {
      updateValue(key, appendUniqueText(values[key], suggestion.text));
    }
  }

  async function startVoice(key: string, label: string) {
    if (voiceState === "recording" && voiceTarget?.key === key) {
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
      setVoiceTarget({ key, label });
      setVoiceState("recording");
      setVoiceMessage(`Идет запись поля «${label}». Нажмите «Остановить запись», когда закончите. Максимум — около минуты.`);

      stopTimerRef.current = window.setTimeout(() => {
        void stopVoiceAndSend();
      }, 55_000);
    } catch {
      setVoiceState("idle");
      setVoiceTarget(null);
      setVoiceMessage("Не удалось получить доступ к микрофону. Проверьте разрешение браузера или заполните поле текстом.");
      cleanupVoice();
    }
  }

  async function stopVoiceAndSend() {
    const target = voiceTarget;
    if (!target) return;

    setVoiceState("uploading");
    setVoiceMessage(`Распознаем запись для поля «${target.label}»...`);
    cleanupVoice();

    const chunks = audioChunksRef.current;
    if (!chunks.length) {
      setVoiceState("idle");
      setVoiceTarget(null);
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

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const payload = await response.json();
      const text = typeof payload?.text === "string" ? payload.text.trim() : "";
      if (!text) {
        throw new Error("Не получилось распознать голос. Можно заполнить поле текстом.");
      }

      appendValue(target.key, text);
      setVoiceMessage("");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "Не получилось распознать голос. Можно заполнить поле текстом.");
    } finally {
      setVoiceState("idle");
      setVoiceTarget(null);
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

  const qualityState = getFormQualityState(module, visibleFieldKeys, values, fieldHints);

  return (
    <form onSubmit={submit} noValidate className="mt-6 grid gap-5">
      {module.slug === "presentation" ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-5">
          <p className="text-lg font-bold text-slate-950">Тип презентации</p>
          <p className="mt-2 text-base text-slate-600">Выберите один из двух вариантов результата.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              ["grant_defense", "Презентация проекта"],
              ["calendar_plan", "Презентация сценарного плана"],
            ].map(([value, label]) => (
              <label key={value} className="flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 p-4 hover:border-blue-300">
                <input
                  type="radio"
                  name="presentation_variant"
                  value={value}
                  checked={(values.presentation_variant || "grant_defense") === value}
                  onChange={(event) => updateValue("presentation_variant", event.target.value)}
                />
                <span className="font-semibold">{label}</span>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {module.fields.map((field, fieldIndex) => {
        const key = getFieldKey(module.slug, fieldIndex, field.label);
        const isLongText = field.type === "textarea";
        const options = key === "scenario_type" ? [...getFieldOptions(key), "Не знаю — помогите выбрать"] : getFieldOptions(key);
        const hasFixedOptions = field.type === "chips" && options.length > 0;
        const selectedMulti = selectedMultiValues(values[key]);
        const inputId = `${module.slug}-${key}`;
        const hint = fieldHints[key];

        return (
          <div key={field.label} className="block rounded-3xl border border-slate-200 bg-white p-5">
            <label htmlFor={inputId} className="block">
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-lg font-bold text-slate-950">{field.label}</span>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${field.required ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
                  {field.required ? "обязательно" : "можно позже"}
                </span>
              </span>
              <span className="mt-2 block text-base text-slate-600">{field.hint}</span>
            </label>

            {isLongText ? (
              <textarea
                id={inputId}
                className="mt-4 min-h-32 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                placeholder={`Например: ${field.example}`}
                value={values[key] || ""}
                onBlur={() => markTouched(key)}
                onChange={(event) => updateValue(key, event.target.value)}
              />
            ) : field.type === "multiselect" ? (
              <div className="mt-4 grid gap-3">
                <div className="flex flex-wrap gap-2">
                  {options.map((option) => (
                    <button
                      type="button"
                      key={option}
                      onClick={() => toggleMultiValue(key, option)}
                      className={`min-h-11 rounded-2xl border px-4 py-2 text-base font-semibold ${
                        selectedMulti.includes(option) ? "border-blue-800 bg-blue-50 text-blue-900" : "border-slate-300 bg-white text-slate-700"
                      }`}
                      aria-pressed={selectedMulti.includes(option)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            ) : field.type === "chips" ? (
              <div className="mt-4 grid gap-3">
                {options.length ? (
                  <div className="flex flex-wrap gap-2">
                    {options.map((option) => (
                      <button
                        type="button"
                        key={option}
                        onClick={() => (option === "Не знаю — помогите выбрать" ? fillUnknownField(key) : updateValue(key, option))}
                        className={`min-h-11 rounded-2xl border px-4 py-2 text-base font-semibold ${
                          values[key] === option ? "border-blue-800 bg-blue-50 text-blue-900" : "border-slate-300 bg-white text-slate-700"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : null}
                {!hasFixedOptions ? (
                  <input
                    id={inputId}
                    className="min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                    placeholder={`Например: ${field.example}`}
                    value={values[key] || ""}
                    onBlur={() => markTouched(key)}
                    onChange={(event) => updateValue(key, event.target.value)}
                  />
                ) : null}
                {scenarioHelper && key === "scenario_type" ? <p className="rounded-2xl bg-blue-50 p-3 text-base leading-7 text-blue-950">{scenarioHelper}</p> : null}
              </div>
            ) : (
              <>
                <input
                  id={inputId}
                  type={field.type === "number" ? "number" : field.type === "email" ? "email" : "text"}
                  min={field.type === "number" ? 1 : undefined}
                  max={key === "employment_percent" ? 100 : undefined}
                  list={options.length ? `${module.slug}-${key}-options` : undefined}
                  className="mt-4 min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                  placeholder={`Например: ${field.example}`}
                  value={values[key] || ""}
                  onBlur={() => markTouched(key)}
                  onChange={(event) => updateValue(key, event.target.value)}
                />
                {options.length ? (
                  <datalist id={`${module.slug}-${key}-options`}>
                    {options.map((option) => (
                      <option key={option} value={option} />
                    ))}
                  </datalist>
                ) : null}
              </>
            )}

            <FieldAssistantHint hint={hint} onSuggestion={(suggestion) => applyHintSuggestion(key, suggestion)} />

            {isLongText ? (
              <div className="mt-3 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void startVoice(key, field.label)}
                  disabled={voiceState === "uploading" || (voiceState === "recording" && voiceTarget?.key !== key)}
                  className="min-h-12 rounded-2xl border border-blue-800 px-4 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50 disabled:border-slate-300 disabled:text-slate-400"
                >
                  {voiceState === "recording" && voiceTarget?.key === key
                    ? "Остановить запись"
                    : voiceState === "uploading" && voiceTarget?.key === key
                      ? "Распознаем..."
                      : voiceButtonLabel(key)}
                </button>
                {values[key] ? (
                  <button
                    type="button"
                    onClick={() => updateValue(key, "")}
                    className="min-h-12 rounded-2xl border border-slate-300 px-4 py-3 text-base font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Очистить
                  </button>
                ) : null}
              </div>
            ) : null}

            {canUseUnknown(field, key) ? (
              <button
                type="button"
                onClick={() => fillUnknownField(key)}
                className="mt-3 min-h-11 rounded-2xl border border-slate-300 px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50"
              >
                Не знаю
              </button>
            ) : null}
          </div>
        );
      })}

      {voiceMessage ? <div className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">{voiceMessage}</div> : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6">
        <p className={`rounded-2xl p-4 text-base leading-7 ${
          resultMatchesCurrent
            ? "bg-slate-100 text-slate-700"
            : resultIsOutdated
              ? "bg-orange-50 text-orange-950"
              : qualityState.className
        }`}>
          {resultMatchesCurrent
            ? "Результат соответствует текущим данным."
            : resultIsOutdated
              ? "Вы изменили данные. Текущий результат относится к предыдущей версии."
              : qualityState.message}
        </p>
        <button
          type="submit"
          disabled={state === "submitting" || resultMatchesCurrent}
          className="mt-4 min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state === "submitting"
            ? module.slug === "support-letter"
              ? "Готовим письмо поддержки..."
              : "Готовим результат..."
            : resultMatchesCurrent
              ? "Результат сформирован"
              : resultIsOutdated
                ? !(usage?.modules?.[module.slug]?.free_attempt_available ?? true) && (usage?.paid_runs ?? 0) <= 0
                  ? "Купить запуск для обновления"
                  : "Обновить результат"
                : launchButtonLabel(module.slug, usage)}
        </button>
        {!(usage?.modules?.[module.slug]?.free_attempt_available ?? true) && (usage?.paid_runs ?? 0) <= 0 ? (
          <button
            type="button"
            onClick={() => router.push(`/pay?return=/m/${module.slug}`)}
            className="mt-3 min-h-14 rounded-2xl border border-blue-800 px-6 py-4 text-lg font-semibold text-blue-800 hover:bg-blue-50"
          >
            Купить запуск или применить промокод
          </button>
        ) : null}
        {message ? (
          <p className={`mt-4 rounded-2xl p-4 text-base leading-7 ${state === "error" ? "bg-red-50 text-red-900" : "bg-green-50 text-green-900"}`}>
            {message}
          </p>
        ) : null}
      </div>
      {resultRunId ? (
        <section id="result" aria-label="Результат работы" data-completed-run-id={lastCompletedRunId || undefined}>
          <ResultViewer runId={resultRunId} projectId={projectId} />
        </section>
      ) : null}
      {lastSubmittedPayload ? <span className="sr-only">Снимок данных результата сохранён</span> : null}
    </form>
  );
}

async function requestAiFieldAssistant(
  moduleSlug: string,
  fieldKey: string,
  fieldLabel: string,
  value: string,
  formContext: Record<string, string>,
): Promise<FieldAssistantHintData | null> {
  try {
    const response = await fetch(apiUrl("/api/field-assistant/analyze"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        module_slug: moduleSlug,
        field_key: fieldKey,
        field_label: fieldLabel,
        value,
        form_context: formContext,
      }),
    });
    if (!response.ok) return null;
    const payload = await response.json();
    return normalizeAssistantHint(payload);
  } catch {
    return null;
  }
}

function getFieldQualityHint(
  moduleSlug: string,
  fieldKey: string,
  field: ModuleField,
  value: string,
  values: Record<string, string>,
  force: boolean,
): FieldAssistantHintData {
  const trimmed = value.trim();
  if (moduleSlug === "legal-acts" && fieldKey === "region" && isRegionalLegalSearch(values.program_level) && !trimmed && force) {
    return errorHint("Для региональных документов нужен регион.");
  }
  if (moduleSlug === "scenario-plan" && fieldKey === "scenario_type" && !trimmed && force) {
    return errorHint("Выберите вид сценарного плана.");
  }
  if (field.required && !trimmed && force) {
    return errorHint("Заполните это поле, чтобы запустить.");
  }

  if (!trimmed) {
    if (moduleSlug === "support-letter") {
      return getSupportLetterMissingHint(fieldKey, force);
    }
    return successHint();
  }

  if (["problem", "event_idea", "project_description", "functionality", "constraints", "team_equipment_constraints"].includes(fieldKey) && countWords(trimmed) < 10) {
    if (fieldKey === "problem") {
      return warningHint("Добавьте, как проявляется проблема или к какому последствию она приводит.", [
        suggestText("add_consequence", "Добавить последствие", "Это ограничивает доступ целевой группы к подходящим возможностям участия."),
        dismissSuggestion(),
      ]);
    }
    return warningHint("Добавьте 1–2 смысловые детали, которые относятся именно к этому полю.", [
      suggestText("add_detail", "Добавить деталь", "Уточните наблюдаемое проявление и ожидаемый результат."),
      dismissSuggestion(),
    ]);
  }

  if (fieldKey === "target_group") {
    if (isBroadTargetGroup(trimmed)) {
      return warningHint("Уточните возраст и социальный статус участников.", [
        suggestText("add_age", "Добавить возраст", "12–22 лет"),
        suggestText("add_status", "Уточнить статус", "учащиеся и молодые специалисты"),
        dismissSuggestion(),
      ]);
    }
    if (!hasAge(trimmed)) {
      return warningHint("Добавьте возраст или диапазон. Например: подростки 12–17 лет.", [
        suggestText("add_age", "Добавить возраст", "12–17 лет"),
        dismissSuggestion(),
      ]);
    }
  }

  if (["problem", "event_idea", "project_description"].includes(fieldKey) && !hasTerritory(trimmed, values)) {
    return warningHint("Укажите территорию в отдельном поле «Регион».", [dismissSuggestion()]);
  }

  if (moduleSlug === "salary") {
    if (fieldKey === "employee_count" && (!isPositiveNumber(trimmed) || toNumber(trimmed) <= 0)) {
      return errorHint("Количество сотрудников должно быть больше нуля.");
    }
    if (fieldKey === "employment_percent" && (!isPositiveNumber(trimmed) || toNumber(trimmed) > 100)) {
      return errorHint("Занятость одного сотрудника не может быть больше 100%.");
    }
    if (fieldKey === "months" && (!isPositiveNumber(trimmed) || toNumber(trimmed) <= 0)) {
      return errorHint("Срок работы должен быть больше нуля.");
    }
    if (fieldKey === "calendar_items" && !trimmed && force) {
      return warningHint("Если номера мероприятий пока неизвестны, их можно добавить вручную позже.");
    }
    if (fieldKey === "functionality" && countWords(trimmed) < 10) {
      return warningHint("Опишите 2–3 обязанности: что делает специалист и к каким мероприятиям относится.");
    }
  }

  if (moduleSlug === "support-letter") {
    const officialHint = getOfficialLanguageHint(fieldKey, trimmed);
    if (officialHint) return officialHint;
    if (fieldKey === "cofinance_block" && (!hasDigits(trimmed) || hasLetters(trimmed) || /[₽.,;:]/.test(trimmed))) {
      return errorHint("Введите оценку вклада только числом, без слова “рублей”.");
    }
    if (["value_keywords", "support_details"].includes(fieldKey) && countWords(trimmed) < 8) {
      return warningHint("Добавьте 1–2 факта: для кого проект, что делает партнер и где это произойдет.", [dismissSuggestion()]);
    }
  }

  if (moduleSlug === "presentation" && fieldKey === "project_description" && trimmed.length < 500) {
    return warningHint("Материала мало. Можно запускать, но добавьте идею, аудиторию, сроки и результаты, если они есть.");
  }

  if (moduleSlug === "scenario-plan" && fieldKey === "participants" && !hasDigits(trimmed)) {
    return warningHint("Добавьте количество команды, участников или зрителей, если оно уже известно.");
  }
  if (moduleSlug === "scenario-plan" && fieldKey === "schedule" && !hasDigits(trimmed)) {
    return errorHint("Укажите число дней и границы времени.");
  }

  return successHint();
}

function getFormQualityState(module: LaryModule, fieldKeys: string[], values: Record<string, string>, hints: FieldHintMap) {
  const hasMissingRequired = module.fields.some((field, index) => field.required && !String(values[fieldKeys[index]] || "").trim());
  const hasBlocking = Object.values(hints).some((hint) => hint.should_block) || hasMissingRequired;
  const hasWarnings = Object.values(hints).some((hint) => hint.status === "warning" || hint.status === "info");

  if (hasBlocking) {
    return {
      message: module.slug === "support-letter" ? "Заполните обязательные поля, чтобы запустить" : "Заполните обязательные поля, чтобы запустить.",
      className: "bg-red-50 text-red-900",
    };
  }
  if (hasWarnings) {
    return { message: "Можно запускать. Есть подсказки, которые улучшат результат.", className: "bg-orange-50 text-orange-950" };
  }
  return { message: "Все обязательные поля заполнены.", className: "bg-green-50 text-green-900" };
}

function applyModuleDefaults(moduleSlug: string, source: Record<string, string>) {
  const values = { ...source };
  if (moduleSlug === "social-research") {
    values.constraints ||= values.details || "";
    delete values.details;
  }
  if (moduleSlug === "scenario-plan") {
    values.event_idea ||= values.description || "";
    values.schedule ||= values.duration || "";
    values.team_equipment_constraints ||= values.details || "";
    delete values.description;
    delete values.duration;
    delete values.details;
  }
  if (moduleSlug === "presentation") {
    values.presentation_variant ||= "grant_defense";
    values.visual_style ||= "Официальный";
    values.slide_count ||= "10–12 рекомендуется";
  }
  if (moduleSlug === "support-letter") {
    values.contest ||= "ПФКИ";
  }
  return values;
}

function voiceButtonLabel(fieldKey: string) {
  return ["problem", "event_idea", "project_description", "functionality"].includes(fieldKey) ? "Наговорить описание" : "Наговорить ответ";
}

function launchButtonLabel(moduleSlug: string, usage: UsagePayload | null) {
  const freeAvailable = usage?.modules?.[moduleSlug]?.free_attempt_available ?? true;
  if (moduleSlug === "support-letter" && (freeAvailable || (usage?.paid_runs ?? 0) > 0)) return "Сформировать DOCX";
  if (freeAvailable) return "Запустить бесплатно";
  if ((usage?.paid_runs ?? 0) > 0) return "Использовать 1 запуск";
  return "Купить запуск модуля";
}

function canUseUnknown(field: ModuleField, key: string) {
  return !field.required && field.type !== "file" && field.type !== "email" && !["contest", "competition", "style", "visual_style", "slide_count"].includes(key);
}

function buildSubmissionInputs(moduleSlug: string, values: Record<string, string>) {
  if (moduleSlug !== "support-letter") return values;
  return {
    ...values,
    contest: "ПФКИ",
    support_types: selectedMultiValues(values.support_types),
  };
}

function selectedMultiValues(value: string | undefined) {
  return String(value || "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getSupportLetterMissingHint(fieldKey: string, force: boolean) {
  if (!force) return successHint();
  const messages: Record<string, string> = {
    value_keywords: "Добавьте ключевые смыслы проекта: для кого, где и почему проект важен.",
    support_types: "Выберите хотя бы один вид поддержки.",
    support_details: "Опишите, что именно делает партнер.",
  };
  return messages[fieldKey] ? errorHint(messages[fieldKey]) : successHint();
}

function normalizeAssistantHint(payload: unknown): FieldAssistantHintData | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Partial<FieldAssistantHintData>;
  const status = ["info", "warning", "error", "success"].includes(String(candidate.status)) ? (candidate.status as FieldAssistantHintData["status"]) : "info";
  const message = String(candidate.message || "").slice(0, 140);
  return {
    status,
    should_block: Boolean(candidate.should_block),
    message,
    suggestions: Array.isArray(candidate.suggestions)
      ? candidate.suggestions.slice(0, 3).map((item) => normalizeSuggestion(item)).filter((item): item is FieldAssistantSuggestion => Boolean(item))
      : [],
    covered_by_fields: Array.isArray(candidate.covered_by_fields) ? candidate.covered_by_fields.slice(0, 12).map(String) : [],
    rewrite_suggestion: typeof candidate.rewrite_suggestion === "string" ? candidate.rewrite_suggestion : null,
  };
}

function successHint(): FieldAssistantHintData {
  return { status: "success", should_block: false, message: "", suggestions: [], covered_by_fields: [] };
}

function warningHint(message: string, suggestions: FieldAssistantSuggestion[] = [dismissSuggestion()]): FieldAssistantHintData {
  return { status: "warning", should_block: false, message: limitMessage(message), suggestions: suggestions.slice(0, 3), covered_by_fields: [] };
}

function errorHint(message: string, suggestions: FieldAssistantSuggestion[] = []): FieldAssistantHintData {
  return { status: "error", should_block: true, message: limitMessage(message), suggestions: suggestions.slice(0, 3), covered_by_fields: [] };
}

function limitMessage(message: string) {
  return message.length > 140 ? `${message.slice(0, 137)}...` : message;
}

function appendUniqueText(current: string | undefined, addition: string) {
  const base = String(current || "").trim();
  if (base.toLocaleLowerCase("ru-RU").includes(addition.trim().toLocaleLowerCase("ru-RU"))) return base;
  return base ? `${base} ${addition}` : addition;
}

function dismissSuggestion(): FieldAssistantSuggestion {
  return { id: "keep_current", label: "Оставить так", operation: "dismiss", text: "" };
}

function suggestText(id: string, label: string, text: string): FieldAssistantSuggestion {
  return { id, label, operation: "suggest_text", text };
}

function normalizeSuggestion(value: unknown): FieldAssistantSuggestion | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<FieldAssistantSuggestion>;
  const operation = candidate.operation === "suggest_text" || candidate.operation === "dismiss" ? candidate.operation : null;
  if (!candidate.id || !candidate.label || !operation) return null;
  return {
    id: String(candidate.id),
    label: String(candidate.label),
    operation,
    text: String(candidate.text || ""),
  };
}

function countWords(value: string) {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

function isBroadTargetGroup(value: string) {
  const normalized = value.toLowerCase().trim().replace(/ё/g, "е");
  const broad = ["молодежь", "дети", "жители", "люди", "население", "общество"];
  return broad.includes(normalized) || (broad.some((word) => normalized === word) && !hasAge(normalized));
}

function hasAge(value: string) {
  return /\d{1,2}\s*[–—-]\s*\d{1,2}|\d{1,2}\+|\b\d{1,2}\s*(лет|года|год)\b/i.test(value);
}

function hasTerritory(value: string, values: Record<string, string>) {
  const text = `${value} ${values.region || ""} ${values.region_value || ""}`.toLowerCase();
  return /(республика|область|край|город|г\.|район|поселок|посёлок|село|деревня|москва|санкт-петербург|казань|екатеринбург|краснодар|татарстан)/i.test(text);
}

function isRegionalLegalSearch(programLevel = "") {
  const lower = programLevel.toLowerCase();
  return lower.includes("регион") && !lower.includes("только федераль");
}

function isPositiveNumber(value: string) {
  return Number.isFinite(toNumber(value)) && toNumber(value) > 0;
}

function toNumber(value: string) {
  return Number(String(value).replace(",", ".").replace(/[^\d.-]/g, ""));
}

function hasLetters(value: string) {
  return /[a-zа-яё]/i.test(value);
}

function hasDigits(value: string) {
  return /\d/.test(value);
}

function getOfficialLanguageHint(fieldKey: string, value: string): FieldAssistantHintData | null {
  if (!["partner_name", "partner_intro_block", "project_title", "support_details", "signatory"].includes(fieldKey)) return null;
  const scan = normalizeForScan(value);
  const offensive = ["негр", "хач", "чурк", "пидор", "пида", "хуй", "хуе", "пизд", "еба", "ебл", "бля", "сука"];
  if (offensive.some((item) => scan.includes(item))) {
    return errorHint("Исправьте формулировку: письмо поддержки должно быть официальным и корректным.");
  }

  const testish = ["кринж", "кринжульки", "asdf", "ыва"];
  const informalSignatory = ["адмирал", "генералиссимус", "повелитель", "магистр", "рыбаков олегинс"];
  if (testish.some((item) => scan.includes(item)) || /^(тест|test)(\s+\d+)?$/.test(scan) || (fieldKey === "signatory" && informalSignatory.some((item) => scan.includes(item)))) {
    return warningHint("Проверьте официальность формулировок: письмо поддержки будет загружаться в заявку ПФКИ.");
  }

  return null;
}

function normalizeForScan(value: string) {
  return value
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[«»„“"'`]+/g, "")
    .replace(/[^0-9a-zа-я]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
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
