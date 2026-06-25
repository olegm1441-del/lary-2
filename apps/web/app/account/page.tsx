import { InfoCallout, PageShell, Section, SecondaryLink } from "../components/lary-ui";

export const metadata = {
  title: "Мои работы — Лари",
};

export default function AccountPage() {
  const rows = [
    ["Сегодня", "Письмо поддержки", "ПФКИ", "Готово"],
    ["Сегодня", "Социальная значимость", "ПФКИ", "Черновик"],
    ["Вчера", "Расчет зарплаты", "ПФКИ", "Сохранено"],
  ];

  return (
    <PageShell>
      <Section eyebrow="Личный кабинет" title="Мои работы, проекты, файлы и запуски" className="bg-white">
        <InfoCallout title="Вход в MVP — через email без пароля">
          Сначала пользователь получает пользу. Email нужен, чтобы не потерять результат и открыть личный кабинет.
        </InfoCallout>
        <div className="mt-8 grid gap-5 lg:grid-cols-[240px_1fr]">
          <nav className="grid content-start gap-2 rounded-3xl border border-slate-200 bg-slate-50 p-4 text-base font-semibold">
            <a className="rounded-2xl bg-blue-800 px-4 py-3 text-white" href="#works">Мои работы</a>
            <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#projects">Проекты</a>
            <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#files">Файлы</a>
            <a className="rounded-2xl px-4 py-3 hover:bg-white" href="#runs">Запуски</a>
          </nav>
          <div className="rounded-3xl border border-slate-200 bg-white p-5">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-base">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-3 pr-4">Дата</th>
                    <th className="py-3 pr-4">Модуль</th>
                    <th className="py-3 pr-4">Конкурс</th>
                    <th className="py-3 pr-4">Статус</th>
                    <th className="py-3">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(([date, module, competition, status]) => (
                    <tr key={`${date}-${module}`} className="border-b border-slate-100">
                      <td className="py-4 pr-4">{date}</td>
                      <td className="py-4 pr-4 font-semibold">{module}</td>
                      <td className="py-4 pr-4">{competition}</td>
                      <td className="py-4 pr-4">{status}</td>
                      <td className="py-4">
                        <SecondaryLink href="/run/demo/result">Открыть</SecondaryLink>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Section>
    </PageShell>
  );
}
