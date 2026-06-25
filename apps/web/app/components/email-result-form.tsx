"use client";

import { FormEvent, useState } from "react";
import { apiUrl, readApiError } from "../lib/api-client";

export function EmailResultForm({ runId }: { runId: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("submitting");
    setMessage("Сохраняем файл в аккаунт и готовим отправку на почту...");

    try {
      const response = await fetch(apiUrl(`/api/module-runs/${runId}/email-file`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const payload = await response.json();
      setState("success");
      setMessage(payload.message || "Файл сохранен в аккаунт. Отправку письма подключим через почтовый сервис.");
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Не получилось сохранить файл. Скачайте его сейчас и попробуйте позже.");
    }
  }

  return (
    <form onSubmit={submit} className="rounded-3xl border border-slate-200 bg-white p-5">
      <h2 className="text-2xl font-bold text-slate-950">Отправить файл на почту</h2>
      <p className="mt-3 text-base leading-7 text-slate-700">
        На почту отправим файл результата. Пароль понадобится для входа в аккаунт по email, где будут храниться ваши файлы.
      </p>
      <label className="mt-5 block">
        <span className="text-base font-semibold text-slate-800">Email</span>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          placeholder="name@example.ru"
          className="mt-2 min-h-12 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 text-base outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
        />
      </label>
      <label className="mt-4 block">
        <span className="text-base font-semibold text-slate-800">Пароль для аккаунта</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          minLength={6}
          placeholder="Минимум 6 символов"
          className="mt-2 min-h-12 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 text-base outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
        />
      </label>
      <button
        type="submit"
        disabled={state === "submitting"}
        className="mt-5 min-h-12 w-full rounded-2xl bg-blue-800 px-5 py-3 text-base font-semibold text-white hover:bg-blue-900 disabled:cursor-wait disabled:bg-slate-400"
      >
        {state === "submitting" ? "Сохраняем..." : "Сохранить и отправить файл"}
      </button>
      {message ? (
        <p className={`mt-4 rounded-2xl p-4 text-base leading-7 ${state === "error" ? "bg-red-50 text-red-900" : "bg-green-50 text-green-900"}`}>{message}</p>
      ) : null}
    </form>
  );
}
