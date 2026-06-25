import Link from "next/link";
import { ResultViewer } from "../../../components/result-viewer";
import { InfoCallout, PageShell, PrimaryLink, SecondaryLink } from "../../../components/lary-ui";
import { getActiveModules } from "../../../lib/lary-data";

export const metadata = {
  title: "Результат работы — Лари",
};

export default async function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const recommended = getActiveModules()[0];

  return (
    <PageShell>
      <section className="bg-white">
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
          <p className="text-base font-semibold uppercase tracking-wide text-green-800">Работа сохранена</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Результат готов к скачиванию</h1>
          <p className="mt-5 max-w-3xl text-xl leading-9 text-slate-700">
            Проверьте текст, скачайте файл и при необходимости запустите следующий модуль для той же заявки.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_360px]">
        <ResultViewer runId={id} />

        <aside className="grid content-start gap-5">
          <InfoCallout title="Не потерять результат">
            Без email работа доступна во временном кабинете 24 часа. Чтобы сохранить надолго, отправьте ссылку себе на почту.
          </InfoCallout>
          <div className="rounded-3xl border border-slate-200 bg-white p-5">
            <p className="text-xl font-bold">Действия</p>
            <div className="mt-4 grid gap-3">
              <SecondaryLink href="/account">Сохранить в мои работы</SecondaryLink>
              <SecondaryLink href="/account">Прикрепить к проекту</SecondaryLink>
              <SecondaryLink href="/modules">Запустить другой модуль</SecondaryLink>
            </div>
          </div>
        </aside>
      </section>

      {recommended ? (
        <section className="mx-auto max-w-7xl px-5 pb-16 sm:px-8">
          <InfoCallout tone="green" title="Следующий полезный шаг">
            После этого результата можно перейти к модулю “{recommended.taskTitle}”.
          </InfoCallout>
          <div className="mt-6">
            <PrimaryLink href={`/m/${recommended.slug}`}>Открыть рекомендованный модуль</PrimaryLink>
          </div>
        </section>
      ) : null}

      <div className="sr-only">
        <Link href="/run/example/result">Пример результата</Link>
      </div>
    </PageShell>
  );
}
