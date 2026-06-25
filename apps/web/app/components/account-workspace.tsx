"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiUrl, readApiError } from "../lib/api-client";

type WorkItem = {
  run_id: string;
  date: string;
  work: string;
  competition: string;
  project: string;
  status: string;
  file_format: string;
  download_path: string;
  actions: string[];
};

export function AccountWorkspace() {
  const [email, setEmail] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [works, setWorks] = useState<WorkItem[]>([]);
  const [mode, setMode] = useState("temporary");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadWorks() {
    setError("");
    try {
      const response = await fetch(apiUrl("/api/account/works"), { credentials: "include" });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setMode(payload.mode || "temporary");
      setWorks(Array.isArray(payload.items) ? payload.items : []);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Не получилось загрузить работы. Попробуйте еще раз.");
    }
  }

  useEffect(() => {
    void loadWorks();
  }, []);

  async function requestMagicLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Отправляем ссылку для входа...");
    setError("");
    try {
      const response = await fetch(apiUrl("/api/auth/magic-link/request"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setMessage(payload.message || "Если email указан верно, ссылка для входа отправлена.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не получилось отправить ссылку.");
    }
  }

  async function createAndAttachProject(runId: string) {
    const title = projectTitle.trim() || "Новый проект";
    setMessage("Создаем проект и прикрепляем работу...");
    setError("");
    try {
      const projectResponse = await fetch(apiUrl("/api/projects"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, competition: "ПФКИ" }),
      });
      if (!projectResponse.ok) throw new Error(await readApiError(projectResponse));
      const project = await projectResponse.json();
      const attachResponse = await fetch(apiUrl(`/api/projects/${project.project_id}/attach`), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId }),
      });
      if (!attachResponse.ok) throw new Error(await readApiError(attachResponse));
      setMessage("Работа прикреплена к проекту.");
      setProjectTitle("");
      await loadWorks();
    } catch (projectError) {
      setError(projectError instanceof Error ? projectError.message : "Не получилось прикрепить работу к проекту.");
    }
  }

  return (
    <div className="mt-8 grid gap-5 lg:grid-cols-[240px_1fr]">
      <nav className="grid content-start gap-2 rounded-3xl border border-slate-200 bg-slate-50 p-4 text-base font-semibold">
        <a className="rounded-2xl bg-blue-800 px-4 py-3 text-white" href="#works">Мои работы</a>
        <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#projects">Проекты</a>
        <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#files">Файлы</a>
        <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#runs">Запуски</a>
        <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#settings">Настройки</a>
        <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#security">Безопасность</a>
      </nav>

      <div className="grid gap-5">
        <section className="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 className="text-2xl font-bold">Войти в личный кабинет</h2>
          <p className="mt-2 text-lg leading-8 text-slate-700">Укажите email, чтобы получить ссылку для входа. Пароль не нужен.</p>
          <form onSubmit={requestMagicLink} className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
            <label className="grid gap-2">
              <span className="text-base font-semibold">Ваш email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="min-h-14 rounded-2xl border border-slate-300 bg-slate-50 px-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <button type="submit" className="self-end min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white">
              Получить ссылку для входа
            </button>
          </form>
          <p className="mt-3 text-base leading-7 text-slate-600">Если вы уже сделали работу без email, она временно доступна в этом браузере 24 часа.</p>
        </section>

        {message ? <p className="rounded-2xl bg-green-50 p-4 text-base leading-7 text-green-900">{message}</p> : null}
        {error ? <p className="rounded-2xl bg-red-50 p-4 text-base leading-7 text-red-900">{error}</p> : null}

        <section id="works" className="rounded-3xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold">Мои работы</h2>
              <p className="mt-1 text-base text-slate-600">{mode === "account" ? "Работы сохранены в аккаунте." : "Временные работы в этом браузере."}</p>
            </div>
            <button type="button" onClick={() => void loadWorks()} className="min-h-11 rounded-2xl border border-slate-300 px-4 py-2 text-base font-semibold">
              Обновить
            </button>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-base">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-3 pr-4">Дата</th>
                  <th className="py-3 pr-4">Работа</th>
                  <th className="py-3 pr-4">Конкурс</th>
                  <th className="py-3 pr-4">Проект</th>
                  <th className="py-3 pr-4">Статус</th>
                  <th className="py-3">Действия</th>
                </tr>
              </thead>
              <tbody>
                {works.map((work) => (
                  <tr key={work.run_id} className="border-b border-slate-100">
                    <td className="py-4 pr-4">{work.date}</td>
                    <td className="py-4 pr-4 font-semibold">{work.work}</td>
                    <td className="py-4 pr-4">{work.competition}</td>
                    <td className="py-4 pr-4">{work.project}</td>
                    <td className="py-4 pr-4">{work.status}</td>
                    <td className="py-4">
                      <div className="flex flex-wrap gap-2">
                        <a href={`/run/${work.run_id}/result`} className="rounded-2xl bg-blue-800 px-4 py-2 font-semibold text-white">Открыть</a>
                        <a href={apiUrl(work.download_path)} className="rounded-2xl border border-slate-300 px-4 py-2 font-semibold">Скачать {work.file_format.toUpperCase()}</a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!works.length ? <p className="py-8 text-lg text-slate-600">Пока нет работ. Запустите любой модуль и вернитесь сюда.</p> : null}
          </div>
        </section>

        <section id="projects" className="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 className="text-2xl font-bold">Проекты</h2>
          <p className="mt-2 text-base leading-7 text-slate-700">Проект — необязательная папка для работ и файлов. Его можно создать после первого результата.</p>
          <label className="mt-4 grid gap-2">
            <span className="text-base font-semibold">Название проекта</span>
            <input value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} placeholder="Например: Музейная заявка" className="min-h-14 rounded-2xl border border-slate-300 bg-slate-50 px-4 text-lg" />
          </label>
          {works[0] ? (
            <button type="button" onClick={() => void createAndAttachProject(works[0].run_id)} className="mt-4 min-h-14 rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white">
              Создать проект и прикрепить последнюю работу
            </button>
          ) : null}
        </section>
      </div>
    </div>
  );
}
