"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { FIELD_KEYS_BY_MODULE, getFieldKey, getFieldOptions, type LaryModule } from "../lib/lary-data";
import { apiUrl, readApiError } from "../lib/api-client";

type RunState = "idle" | "submitting" | "error";
type VoiceState = "idle" | "recording" | "uploading";
type VoiceTarget = { key: string; label: string };
type ValidationHint = { field_key: string; message: string; tone: string };

export function ModuleRunner({ module }: { module: LaryModule }) {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, string>>({});
  const [state, setState] = useState<RunState>("idle");
  const [message, setMessage] = useState("");
  const [voiceMessage, setVoiceMessage] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceTarget, setVoiceTarget] = useState<VoiceTarget | null>(null);
  const [validationHints, setValidationHints] = useState<ValidationHint[]>([]);
  const [isCheckingInputs, setIsCheckingInputs] = useState(false);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const sourceSampleRateRef = useRef(44100);
  const stopTimerRef = useRef<number | null>(null);

  const presentationVariant = useMemo(() => {
    if (module.slug !== "presentation") return undefined;
    return values.presentation_variant || "grant_defense";
  }, [module.slug, values.presentation_variant]);

  const hasAnyInput = useMemo(() => Object.values(values).some((value) => value.trim().length > 0), [values]);
  const fieldKeys = FIELD_KEYS_BY_MODULE[module.slug] || [];

  useEffect(() => {
    if (!hasAnyInput) {
      setValidationHints([]);
      setIsCheckingInputs(false);
      return;
    }

    let cancelled = false;
    setIsCheckingInputs(true);
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(apiUrl(`/api/modules/${module.slug}/validate-inputs`), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inputs: values }),
        });
        if (!response.ok) throw new Error(await readApiError(response));
        const payload = await response.json();
        if (!cancelled) setValidationHints(Array.isArray(payload.hints) ? payload.hints : []);
      } catch {
        if (!cancelled) setValidationHints([]);
      } finally {
        if (!cancelled) setIsCheckingInputs(false);
      }
    }, 550);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [hasAnyInput, module.slug, values]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("submitting");
    setMessage("Лари готовит результат. Данные сохранены.");

    try {
      const response = await fetch(apiUrl("/api/module-runs"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module_slug: module.slug,
          inputs: values,
          presentation_variant: presentationVariant,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const payload = await response.json();
      router.push(`/run/${payload.run_id}/result`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту.");
    }
  }

  function updateValue(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function appendValue(key: string, value: string) {
    setValues((current) => ({
      ...current,
      [key]: current[key] ? `${current[key]}\n${value}` : value,
    }));
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
      setVoiceMessage(`Голос распознан и добавлен в поле «${target.label}». Проверьте текст перед запуском модуля.`);
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

  return (
    <form onSubmit={submit} className="mt-6 grid gap-5">
      {module.slug === "presentation" ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-5">
          <p className="text-lg font-bold text-slate-950">Тип презентации</p>
          <p className="mt-2 text-base text-slate-600">Выберите один из двух MVP-подвариантов.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              ["grant_defense", "Защита заявки"],
              ["calendar_plan", "Демонстрация календарного плана"],
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
        const options = getFieldOptions(key);
        const fieldHints = validationHints.filter((hint) => hint.field_key === key || (key === "description" && hint.field_key === "problem"));

        return (
          <label key={field.label} className="block rounded-3xl border border-slate-200 bg-white p-5">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-lg font-bold text-slate-950">{field.label}</span>
              <span className={`rounded-full px-2 py-1 text-xs font-semibold ${field.required ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
                {field.required ? "обязательно" : "можно позже"}
              </span>
            </span>
            <span className="mt-2 block text-base text-slate-600">{field.hint}</span>
            {isLongText ? (
              <textarea
                className="mt-4 min-h-32 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                placeholder={`Например: ${field.example}`}
                value={values[key] || ""}
                onChange={(event) => updateValue(key, event.target.value)}
                required={field.required}
              />
            ) : field.type === "chips" ? (
              <div className="mt-4 grid gap-3">
                {options.length ? (
                  <div className="flex flex-wrap gap-2">
                    {options.map((option) => (
                      <button
                        type="button"
                        key={option}
                        onClick={() => updateValue(key, option)}
                        className={`min-h-11 rounded-2xl border px-4 py-2 text-base font-semibold ${
                          values[key] === option ? "border-blue-800 bg-blue-50 text-blue-900" : "border-slate-300 bg-white text-slate-700"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : null}
                <input
                  className="min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                  placeholder={`Например: ${field.example}`}
                  value={values[key] || ""}
                  onChange={(event) => updateValue(key, event.target.value)}
                  required={field.required}
                />
              </div>
            ) : (
              <>
                <input
                  list={options.length ? `${module.slug}-${key}-options` : undefined}
                  className="mt-4 min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                  placeholder={`Например: ${field.example}`}
                  value={values[key] || ""}
                  onChange={(event) => updateValue(key, event.target.value)}
                  required={field.required}
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
            {fieldHints.length ? (
              <div className="mt-3 grid gap-2">
                {fieldHints.map((hint) => (
                  <p key={hint.message} className="rounded-2xl bg-orange-50 p-3 text-base leading-7 text-orange-950">
                    {hint.message}
                  </p>
                ))}
              </div>
            ) : null}
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
                      : "Наговорить"}
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
          </label>
        );
      })}

      {voiceMessage ? <div className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">{voiceMessage}</div> : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6">
        {hasAnyInput ? (
          <div className="mb-6">
            <h2 className="text-3xl font-bold">Проверка перед запуском</h2>
            <div className="mt-5 grid gap-3">
              {isCheckingInputs ? (
                <div className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">Лари проверяет, достаточно ли данных для первого черновика...</div>
              ) : validationHints.length ? (
                validationHints.map((hint) => (
                  <div key={`${hint.field_key}-${hint.message}`} className="rounded-2xl bg-orange-50 p-4 text-base leading-7 text-orange-950">
                    {hint.message}
                  </div>
                ))
              ) : (
                <div className="rounded-2xl bg-green-50 p-4 text-base leading-7 text-green-950">Данных достаточно для первого черновика. Перед подачей результат все равно нужно проверить вручную.</div>
              )}
            </div>
          </div>
        ) : null}
        <button
          type="submit"
          disabled={state === "submitting"}
          className="mt-6 min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state === "submitting" ? "Готовим результат..." : "Запустить модуль бесплатно"}
        </button>
        {message ? (
          <p className={`mt-4 rounded-2xl p-4 text-base leading-7 ${state === "error" ? "bg-red-50 text-red-900" : "bg-green-50 text-green-900"}`}>
            {message}
          </p>
        ) : null}
      </div>
    </form>
  );
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
