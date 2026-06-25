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
        <p className="text-2xl font-bold">Не получилось подготовить ответ</p>
        <p className="mt-3 text-lg leading-8">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950">
        <p className="text-2xl font-bold">Лари готовит результат</p>
        <p className="mt-3 text-lg leading-8">Обычно это занимает меньше минуты. Не закрывайте страницу, данные уже сохранены.</p>
      </div>
    );
  }

  if (result.status !== "completed") {
    return (
      <div className="rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950">
        <p className="text-2xl font-bold">{result.status === "failed" ? "Не получилось подготовить ответ" : "Лари готовит результат"}</p>
        <p className="mt-3 text-lg leading-8">
          {result.status === "failed"
            ? "Данные сохранены. Попробуйте повторить запуск через минуту или напишите в поддержку."
            : "Обычно это занимает меньше минуты. Не закрывайте страницу, данные уже сохранены."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Предпросмотр</p>
          <h2 className="mt-2 text-3xl font-bold">{result.title}</h2>
        </div>
        <span className="rounded-full bg-green-50 px-4 py-2 text-base font-semibold text-green-800">Готово</span>
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
      <div className="mt-8 flex flex-wrap gap-4">
        {Object.entries(result.downloads).map(([format, href]) => (
          <a
            key={format}
            href={apiUrl(href)}
            className="min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold uppercase text-white hover:bg-blue-900"
          >
            Скачать {format}
          </a>
        ))}
      </div>
    </div>
  );
}
