"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import type { LaryModule } from "../lib/lary-data";
import { apiUrl, readApiError } from "../lib/api-client";

type RunState = "idle" | "submitting" | "error";

export function ModuleRunner({ module }: { module: LaryModule }) {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, string>>({});
  const [state, setState] = useState<RunState>("idle");
  const [message, setMessage] = useState("");
  const [voiceMessage, setVoiceMessage] = useState("");

  const presentationVariant = useMemo(() => {
    if (module.slug !== "presentation") return undefined;
    return values.presentation_variant || "grant_defense";
  }, [module.slug, values.presentation_variant]);

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

  function startVoice(label: string) {
    setVoiceMessage(`Голосовой ввод для поля «${label}» будет отправлять аудио в SaluteSpeech через backend. Сейчас можно заполнить поле текстом.`);
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

      {module.fields.map((field) => {
        const key = field.label.toLowerCase().replace(/\s+/g, "_");
        const isLongText = field.type === "textarea";

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
            ) : (
              <input
                className="mt-4 min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
                placeholder={`Например: ${field.example}`}
                value={values[key] || ""}
                onChange={(event) => updateValue(key, event.target.value)}
                required={field.required}
              />
            )}
            {isLongText ? (
              <button
                type="button"
                onClick={() => startVoice(field.label)}
                className="mt-3 min-h-12 rounded-2xl border border-blue-800 px-4 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50"
              >
                Наговорить
              </button>
            ) : null}
          </label>
        );
      })}

      {voiceMessage ? <div className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">{voiceMessage}</div> : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-6">
        <h2 className="text-3xl font-bold">Проверка перед запуском</h2>
        <div className="mt-5 grid gap-3">
          {module.aiHints.map((hint) => (
            <div key={hint} className="rounded-2xl bg-blue-50 p-4 text-base leading-7 text-blue-950">
              {hint}
            </div>
          ))}
        </div>
        <button
          type="submit"
          disabled={state === "submitting"}
          className="mt-6 min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state === "submitting" ? "Готовим результат..." : `Запустить модуль за 320 руб / бесплатно в первый раз`}
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
