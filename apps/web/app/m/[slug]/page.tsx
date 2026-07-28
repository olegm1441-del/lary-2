import Link from "next/link";
import { notFound } from "next/navigation";
import { ModuleRunner } from "../../components/module-runner";
import { ModuleAttemptStatus } from "../../components/module-attempt-status";
import { InfoCallout, PageShell, WorkPanel } from "../../components/lary-ui";
import { getModuleBySlug, getModuleSlugs } from "../../lib/lary-data";
import { ContestSelector } from "../../components/contest-selector";
import { ModuleShell } from "../../components/module-shell";
import { getModuleProfile, getPublicContests, hasRealExample } from "../../lib/product-registry";
import { ProjectContestSync } from "../../components/project-contest-sync";
import { buildModuleRoute } from "../../lib/module-route";

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

export default async function ModulePage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    example?: string;
    contest?: string;
    mode?: string;
    project_id?: string;
    intent?: string;
    change_contest?: string;
  }>;
}) {
  const { slug } = await params;
  const query = await searchParams;
  const laryModule = getModuleBySlug(slug);

  if (!laryModule) notFound();

  const isComingSoon = laryModule.status === "coming_soon";
  const showExample = query.example === "1";
  const selectedContest = query.contest ? getPublicContests().find((contest) => contest.slug === query.contest) : undefined;
  const profile = selectedContest ? getModuleProfile(laryModule.slug, selectedContest.slug) : undefined;
  const realExampleContests = getPublicContests()
    .filter((contest) => hasRealExample(laryModule.slug, contest.slug))
    .map((contest) => contest.slug);
  const showRunner = profile?.status === "ready" && query.mode === "start" && !showExample;
  const formTitle =
    laryModule.slug === "support-letter"
      ? "Заполните данные партнера и вклада"
      : "Заполните то, что уже известно";
  const formDescription =
    laryModule.slug === "support-letter"
      ? "Пишите коротко и фактами. Лари соберет письмо по шаблону: отдельно подставит данные партнера, аккуратно сформулирует значимость проекта и опишет вклад партнера."
      : "Лари обработает ответы и подготовит рабочий файл для скачивания.";
  const shellSteps = showExample && profile?.status === "ready"
    ? [
        { id: "contest", label: "Конкурс" },
        { id: "example", label: "Пример" },
      ]
    : [
        { id: "contest", label: "Конкурс" },
        { id: "data", label: "Данные", disabled: profile?.status !== "ready" },
        { id: "result", label: "Результат", disabled: true },
      ];

  return (
    <PageShell>
      <section className="bg-white">
        <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:py-16">
          <div>
            <Link href="/modules" className="inline-flex min-h-11 items-center text-base font-semibold text-blue-800 hover:underline">
              ← Все модули
            </Link>
            <p className="mt-6 text-base font-semibold uppercase tracking-wide text-blue-800">
              {selectedContest ? `Конкурс: ${selectedContest.name}` : "Сначала выберите конкурс"}
            </p>
            <h1 className="mt-3 max-w-4xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">{laryModule.taskTitle}</h1>
            <p className="mt-5 max-w-3xl text-xl leading-9 text-slate-700">{laryModule.promise}</p>
            <div className="mt-6 flex flex-wrap gap-3 text-base">
              <span className="rounded-full bg-slate-100 px-4 py-2 font-semibold">{laryModule.duration}</span>
              <span className="rounded-full bg-slate-100 px-4 py-2 font-semibold">{laryModule.outputFormats.join(" + ")}</span>
              {!isComingSoon ? <ModuleAttemptStatus moduleSlug={laryModule.slug} className="rounded-full px-4 py-2" /> : null}
            </div>
          </div>
        </div>
      </section>

      <ModuleShell
        moduleSlug={laryModule.slug}
        steps={shellSteps}
        utility={selectedContest ? <WorkPanel module={laryModule} contestName={selectedContest.name} /> : null}
      >
          <ProjectContestSync
            moduleSlug={laryModule.slug}
            projectId={query.project_id}
            selectedContest={selectedContest?.slug}
            mode={query.mode}
            example={query.example}
            intent={query.intent}
            changeContest={query.change_contest === "1"}
            realExampleContests={realExampleContests}
          />
          {!selectedContest ? (
            <ContestSelector
              contests={getPublicContests()}
              moduleSlug={laryModule.slug}
              projectId={query.project_id}
              mode={query.mode}
              example={query.example}
              intent={query.intent}
              realExampleContests={realExampleContests}
            />
          ) : profile?.status !== "ready" ? (
            <div id="contest" className="rounded-3xl border border-orange-200 bg-orange-50 p-6">
              <h2 className="text-3xl font-bold text-slate-950">Для этого конкурса модуль пока готовится.</h2>
              <p className="mt-3 text-lg leading-8 text-slate-700">Выберите другой конкурс, чтобы продолжить сейчас.</p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Link href={buildModuleRoute({ moduleSlug: laryModule.slug, projectId: query.project_id, changeContest: true })} className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-blue-800 px-5 py-3 text-base font-semibold text-white">
                  Выбрать другой конкурс
                </Link>
                <Link href="/modules" className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-base font-semibold text-slate-900">
                  Вернуться к модулям
                </Link>
              </div>
            </div>
          ) : !showRunner && !showExample ? (
            <>
              <section id="contest" className="rounded-2xl border border-green-200 bg-green-50 p-4">
                <p className="text-base font-semibold text-green-900">{selectedContest.name} выбран</p>
              </section>
              <section id="data" className="mt-6 rounded-3xl border border-blue-200 bg-blue-50 p-6">
                <p className="text-base font-semibold uppercase tracking-wide text-blue-800">{selectedContest.name}</p>
                <h2 className="mt-2 text-3xl font-bold">Как продолжить?</h2>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <Link href={buildModuleRoute({ moduleSlug: laryModule.slug, contestSlug: selectedContest.slug, projectId: query.project_id, mode: "start" })} className="inline-flex min-h-14 items-center justify-center rounded-2xl bg-blue-800 px-5 py-4 text-lg font-semibold text-white">
                    Запустить модуль
                  </Link>
                  {hasRealExample(laryModule.slug, selectedContest.slug) ? (
                    <Link href={buildModuleRoute({ moduleSlug: laryModule.slug, contestSlug: selectedContest.slug, projectId: query.project_id, example: "1" })} className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-blue-800 bg-white px-5 py-4 text-lg font-semibold text-blue-900">
                      Посмотреть пример
                    </Link>
                  ) : (
                    <span className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 py-4 text-center text-base font-semibold text-slate-500">
                      Пример для этого конкурса пока готовится
                    </span>
                  )}
                </div>
                <Link href={buildModuleRoute({ moduleSlug: laryModule.slug, projectId: query.project_id, changeContest: true })} className="mt-5 inline-flex min-h-11 items-center text-base font-semibold text-blue-800 hover:underline">
                  Выбрать другой конкурс
                </Link>
              </section>
            </>
          ) : (
            <>
              <section id="contest" className="rounded-2xl border border-green-200 bg-green-50 p-4">
                <p className="text-base font-semibold text-green-900">{selectedContest.name} выбран</p>
              </section>
              <section id={showExample ? "example" : "data"} className="mt-6">
              {laryModule.slug !== "salary" ? (
                <div className="rounded-3xl border border-slate-200 bg-white p-6">
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Ответьте на вопросы</p>
                  <h2 className="mt-2 text-3xl font-bold">{formTitle}</h2>
                  <p className="mt-3 text-lg leading-8 text-slate-700">{formDescription}</p>
                </div>
              ) : null}
              {showExample ? <ExampleResult slug={laryModule.slug} title={laryModule.taskTitle} /> : null}
              {showRunner ? <ModuleRunner module={laryModule} contestSlug={selectedContest.slug} profileVersion={profile.profile_version} projectId={query.project_id} /> : null}
              </section>
            </>
          )}
          {selectedContest && profile?.status === "ready" && (showRunner || showExample) ? (
            <div className="mt-8 grid content-start gap-5 xl:hidden">
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
              {laryModule.slug === "salary" ? (
                <InfoCallout title="Источники расчета">
                  Лари проверяет данные ГородРабот и портала «Работа России» и использует самый высокий подтвержденный показатель со ссылкой.
                </InfoCallout>
              ) : null}
            </div>
          ) : null}
      </ModuleShell>
    </PageShell>
  );
}

function ExampleResult({ slug, title }: { slug: string; title: string }) {
  const sample = EXAMPLE_RESULTS[slug] || EXAMPLE_RESULTS["social-research"];

  return (
    <div className="mt-6 rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950">
      <p className="text-sm font-semibold uppercase tracking-wide">Пример результата</p>
      <h2 className="mt-2 text-2xl font-bold">{title}</h2>
      <div className="mt-4 grid gap-3">
        {sample.map((item) => (
          <section key={item.title} className="rounded-2xl bg-white p-4">
            <h3 className="text-lg font-bold">{item.title}</h3>
            <p className="mt-2 text-base leading-7 text-slate-700">{item.body}</p>
          </section>
        ))}
      </div>
    </div>
  );
}

const EXAMPLE_RESULTS: Record<string, Array<{ title: string; body: string }>> = {
  "social-research": [
    { title: "Ситуация", body: "Краткое описание проблемы на выбранной территории и группы, которой она касается." },
    { title: "Источники", body: "Официальный источник, исследование/статистика, справочный источник — с пометками для ручной проверки." },
  ],
  "legal-acts": [
    { title: "Федеральный уровень", body: "Название программы или акта, официальный источник проверки и связь с темой проекта." },
    { title: "Региональный уровень", body: "Документы субъекта РФ и предупреждение проверить актуальную редакцию." },
  ],
  salary: [
    {
      title: "Исходные данные",
      body: "Должность: координатор проекта. Регион: Свердловская область. Период работы в проекте: 4 месяца. Занятость: 40% рабочего времени. Источник расчета: средняя заработная плата по выбранной должности и региону за актуальный доступный год.",
    },
    {
      title: "Источник зарплаты",
      body: "По данным открытого источника по рынку труда, средняя заработная плата координатора в Свердловской области за 2024 год составляет 68 372 рубля в месяц.",
    },
    {
      title: "Функционал",
      body: "Координатор проекта обеспечивает организационное сопровождение участников и команды: ведет списки участников, согласует расписание, назначает и сопровождает организационные встречи, предупреждает участников об изменениях, фиксирует посещаемость, помогает собрать анкеты и обратную связь, передает информацию руководителю проекта и ответственным за мероприятия. Работа координатора необходима на всех этапах, где есть взаимодействие с участниками, расписанием, площадками и отчетными материалами.",
    },
    {
      title: "Календарный план",
      body: "Координатор задействован в мероприятиях календарного плана № 1.1–1.4, 2.1–2.3, 3.1.",
    },
    {
      title: "Расчет",
      body: "68 372 руб. × 40% × 4 месяца = 109 395,20 руб. К включению в бюджет: 109 395 руб.",
    },
    {
      title: "Обоснование",
      body: "Сумма рассчитана пропорционально фактической занятости координатора в проекте. В бюджет включается только та часть оплаты труда, которая относится к выполнению задач заявляемого проекта. Занятость 40% обоснована регулярной коммуникацией с участниками и командой, сопровождением нескольких мероприятий календарного плана, контролем посещаемости, переносами занятий/встреч и сбором отчетных данных.",
    },
    {
      title: "Софинансирование",
      body: "Источник софинансирования: собственные средства заявителя / собственные средства ИП / привлеченные средства партнера согласно письму поддержки.",
    },
  ],
  "support-letter": [
    { title: "DOCX-письмо", body: "Письмо по шаблону ПФКИ с названием партнера, описанием поддержки, вкладом и подписантом." },
    { title: "Чек-лист", body: "Дата, исходящий номер, подпись, печать при наличии и подтверждение суммы вклада." },
  ],
  presentation: [
    { title: "Структура", body: "Обложка, идея, актуальность, аудитория, механика, календарный план, команда, результаты." },
    { title: "Файл", body: "Редактируемая PPTX-презентация в выбранном стиле." },
  ],
  "scenario-plan": [
    { title: "Блоки события", body: "Подготовка, вход участника, основная часть, финал, переходы и роли команды." },
    { title: "Тайминг", body: "Поминутный или дневной план с точками ручной проверки." },
  ],
};
