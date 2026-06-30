"use client";

import { useEffect, useState } from "react";
import { apiUrl, readApiError } from "../lib/api-client";

type ResultPayload = {
  run_id: string;
  status: string;
  module_slug: string;
  title: string;
  summary: string;
  sections: Array<{ title: string; body: string }>;
  downloads: Record<string, string>;
};

export function ResultViewer({ runId }: { runId: string }) {
  const [result, setResult] = useState<ResultPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError("");
      try {
        const response = await fetch(apiUrl(`/api/module-runs/${runId}/result`), { credentials: "include" });
        if (!response.ok) throw new Error(await readApiError(response));
        const payload = await response.json();
        if (!cancelled) setResult(payload);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту.");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (error) {
    return (
      <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-950">
        <p className="text-2xl font-bold">Не получилось подготовить результат</p>
        <p className="mt-3 text-lg leading-8">{error}</p>
        <FailedActions runId={runId} />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950">
        <p className="text-2xl font-bold">Лари готовит результат</p>
        <p className="mt-3 text-lg leading-8">Данные сохранены. Обычно это занимает меньше минуты. Не закрывайте страницу.</p>
        <div className="mt-5 h-4 w-full animate-pulse rounded-full bg-blue-100" aria-hidden="true" />
      </div>
    );
  }

  if (result.status !== "completed") {
    return (
      <div className="rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950">
        <p className="text-2xl font-bold">{result.status === "failed" ? "Не получилось подготовить результат" : "Лари готовит результат"}</p>
        <p className="mt-3 text-lg leading-8">
          {result.status === "failed"
            ? "Данные сохранены. Попробуйте еще раз через минуту или напишите в поддержку."
            : "Данные сохранены. Обычно это занимает меньше минуты. Не закрывайте страницу."}
        </p>
        {result.status === "failed" ? <FailedActions runId={runId} /> : <div className="mt-5 h-4 w-full animate-pulse rounded-full bg-blue-100" aria-hidden="true" />}
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-green-800">Результат готов</p>
          <h2 className="mt-2 text-3xl font-bold">{result.title}</h2>
        </div>
        <span className="rounded-full bg-green-50 px-4 py-2 text-base font-semibold text-green-800">Готово</span>
      </div>
      <div className="mt-6 rounded-3xl border border-blue-100 bg-blue-50 p-5">
        <h3 className="text-xl font-bold text-blue-950">Скачать файл</h3>
        <ResultActions result={result} onResult={setResult} />
      </div>
      <p className="mt-5 text-lg leading-8 text-slate-700">{result.summary}</p>
      <div className="mt-6 grid gap-4">
        {result.sections.map((section) => (
          <section key={section.title} className="rounded-2xl bg-slate-50 p-5">
            <h3 className="text-xl font-bold">{section.title}</h3>
            <p className="mt-2 whitespace-pre-line text-base leading-7 text-slate-700">{section.body}</p>
          </section>
        ))}
      </div>
    </div>
  );
}

function ResultActions({ result, onResult }: { result: ResultPayload; onResult: (result: ResultPayload) => void }) {
  const preferred = result.downloads.docx ? "docx" : result.downloads.pptx ? "pptx" : Object.keys(result.downloads)[0];
  const ordered = [
    ...(preferred ? [[preferred, result.downloads[preferred]]] : []),
    ...Object.entries(result.downloads).filter(([format]) => format !== preferred),
  ];
  const copyAvailable = result.module_slug !== "support-letter";

  async function copyResult() {
    const text = [result.title, result.summary, ...result.sections.map((section) => `${section.title}\n${section.body}`)].join("\n\n");
    await navigator.clipboard?.writeText(text);
  }

  async function improveResult() {
    const instruction = window.prompt("Что улучшить в результате?", "Сделать текст понятнее и официальнее");
    if (!instruction) return;
    const response = await fetch(apiUrl(`/api/module-runs/${result.run_id}/improve`), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instruction }),
    });
    if (!response.ok) {
      window.alert(await readApiError(response));
      return;
    }
    onResult(await response.json());
  }

  return (
    <div className="mt-6 grid gap-3 sm:flex sm:flex-wrap">
      {ordered.map(([format, href], index) => (
        <a
          key={format}
          href={apiUrl(href)}
          className={
            index === 0
              ? "inline-flex min-h-14 items-center justify-center rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold uppercase text-white hover:bg-blue-900"
              : "inline-flex min-h-14 items-center justify-center rounded-2xl border border-slate-300 px-6 py-4 text-lg font-semibold uppercase text-slate-900 hover:bg-slate-50"
          }
        >
          Скачать {format.toUpperCase()}
        </a>
      ))}
      {copyAvailable ? (
        <button type="button" onClick={() => void copyResult()} className="min-h-14 rounded-2xl border border-slate-300 px-6 py-4 text-lg font-semibold text-slate-900 hover:bg-slate-50">
          Скопировать
        </button>
      ) : null}
      <button id="improve" type="button" onClick={() => void improveResult()} className="min-h-14 rounded-2xl border border-slate-300 px-6 py-4 text-lg font-semibold text-slate-900 hover:bg-slate-50">
        Улучшить
      </button>
      <a href="#email-result" className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-slate-300 px-6 py-4 text-lg font-semibold text-slate-900 hover:bg-white">
        Отправить на email
      </a>
      <a href="/account#projects" className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-slate-300 px-6 py-4 text-lg font-semibold text-slate-900 hover:bg-white">
        Прикрепить к проекту
      </a>
    </div>
  );
}

function FailedActions({ runId }: { runId: string }) {
  return (
    <div className="mt-5 flex flex-wrap gap-3">
      <a href={`/run/${runId}/result`} className="min-h-12 rounded-2xl bg-blue-800 px-5 py-3 text-base font-semibold text-white hover:bg-blue-900">
        Попробовать еще раз
      </a>
      <a href="/modules" className="min-h-12 rounded-2xl border border-slate-300 px-5 py-3 text-base font-semibold text-slate-900 hover:bg-white">
        Вернуться к форме
      </a>
      <a href="/contacts" className="min-h-12 rounded-2xl border border-slate-300 px-5 py-3 text-base font-semibold text-slate-900 hover:bg-white">
        Написать в поддержку
      </a>
    </div>
  );
}
