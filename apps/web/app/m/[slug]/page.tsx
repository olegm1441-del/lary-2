import Link from "next/link";
import { notFound } from "next/navigation";
import { ModuleRunner } from "../../components/module-runner";
import { ModuleAttemptStatus } from "../../components/module-attempt-status";
import { InfoCallout, PageShell, PrimaryLink, SecondaryLink, WorkPanel } from "../../components/lary-ui";
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

export default async function ModulePage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<{ example?: string }> }) {
  const { slug } = await params;
  const query = await searchParams;
  const laryModule = getModuleBySlug(slug);

  if (!laryModule) notFound();

  const isComingSoon = laryModule.status === "coming_soon";
  const showExample = query.example === "1";
  const formTitle =
    laryModule.slug === "support-letter"
      ? "Заполните данные партнера и вклада"
      : laryModule.slug === "salary"
        ? "Заполните расчет по должностям"
        : "Заполните то, что уже известно";
  const formDescription =
    laryModule.slug === "support-letter"
      ? "Пишите коротко и фактами. Лари соберет письмо по шаблону: отдельно подставит данные партнера, аккуратно сформулирует значимость проекта и опишет вклад партнера."
      : laryModule.slug === "salary"
        ? "Добавьте одну или несколько должностей. Лари проверит доступные источники зарплат, выберет самый высокий подтвержденный показатель и соберет расчет с обоснованием."
      : "Лари обработает ответы и подготовит рабочий файл для скачивания.";

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
            Сейчас можно посмотреть будущий сценарий и оставить email на странице контактов. Для текущей версии используйте шесть активных модулей.
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
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Ответьте на вопросы</p>
                <h2 className="mt-2 text-3xl font-bold">{formTitle}</h2>
                <p className="mt-3 text-lg leading-8 text-slate-700">{formDescription}</p>
              </div>
              {showExample ? <ExampleResult slug={laryModule.slug} title={laryModule.taskTitle} /> : null}
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

        </>
      )}
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
