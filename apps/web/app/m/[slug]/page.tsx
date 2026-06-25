import Link from "next/link";
import { notFound } from "next/navigation";
import { ModuleRunner } from "../../components/module-runner";
import { ModuleAttemptStatus } from "../../components/module-attempt-status";
import { ApiStatePanel, InfoCallout, PageShell, PrimaryLink, SecondaryLink, WorkPanel } from "../../components/lary-ui";
import { getModuleBySlug, getModuleSlugs } from "../../lib/lary-data";

export function generateStaticParams() {
  return getModuleSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const laryModule = getModuleBySlug(slug);

  return {
    title: laryModule ? `${laryModule.title} — Лари` : "Модуль Лари",
  };
}

export default async function ModulePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const laryModule = getModuleBySlug(slug);

  if (!laryModule) notFound();

  const isComingSoon = laryModule.status === "coming_soon";

  return (
    <PageShell>
      <section className="bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_320px] lg:py-16">
          <div>
            <Link href="/modules" className="text-base font-semibold text-blue-800 hover:underline">
              ← Все модули
            </Link>
            <p className="mt-6 text-base font-semibold uppercase tracking-wide text-blue-800">Конкурс: {laryModule.competition} ✓</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">{laryModule.taskTitle}</h1>
            <p className="mt-5 max-w-3xl text-xl leading-9 text-slate-700">{laryModule.promise}</p>
            <div className="mt-6 flex flex-wrap gap-3 text-base">
              <span className="rounded-full bg-slate-100 px-4 py-2 font-semibold">{laryModule.duration}</span>
              <span className="rounded-full bg-slate-100 px-4 py-2 font-semibold">{laryModule.outputFormats.join(" + ")}</span>
              {!isComingSoon ? <ModuleAttemptStatus moduleSlug={laryModule.slug} className="rounded-full px-4 py-2" /> : null}
            </div>
          </div>
          <WorkPanel module={laryModule} />
        </div>
      </section>

      {isComingSoon ? (
        <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8">
          <InfoCallout tone="orange" title="Этот модуль предусмотрен в архитектуре, но еще не включен в первый запуск">
            Сейчас можно посмотреть будущий сценарий и оставить email на странице контактов. Для текущего MVP используйте шесть активных модулей.
          </InfoCallout>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <PrimaryLink href="/contacts">Оставить заявку</PrimaryLink>
            <SecondaryLink href="/modules">Вернуться к модулям</SecondaryLink>
          </div>
        </section>
      ) : (
        <>
          <section className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_320px]">
            <div>
              <div className="rounded-3xl border border-slate-200 bg-white p-6">
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Форма модуля</p>
                <h2 className="mt-2 text-3xl font-bold">Ответьте на несколько вопросов</h2>
                <p className="mt-3 text-lg leading-8 text-slate-700">
                  Лари проверит ответы и подготовит результат для скачивания.
                </p>
              </div>
              <ModuleRunner module={laryModule} />
            </div>
            <div className="grid content-start gap-5">
              <InfoCallout title="Что получится">
                <ul className="grid gap-2">
                  {laryModule.resultPreview.map((item) => (
                    <li key={item}>✓ {item}</li>
                  ))}
                </ul>
              </InfoCallout>
              <InfoCallout tone="green" title="После результата">
                Можно скачать файл, улучшить текст, отправить себе на почту или прикрепить к проекту.
              </InfoCallout>
            </div>
          </section>

          <section className="mx-auto max-w-7xl px-5 pb-14 sm:px-8">
            <h2 className="text-3xl font-bold">Состояния API для этого экрана</h2>
            <div className="mt-6">
              <ApiStatePanel />
            </div>
          </section>
        </>
      )}
    </PageShell>
  );
}
