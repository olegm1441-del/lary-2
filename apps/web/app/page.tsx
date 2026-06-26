import Link from "next/link";
import { ApiStatePanel, InfoCallout, ModuleCard, PageShell, PrimaryLink, Section, SecondaryLink } from "./components/lary-ui";
import { getActiveModules, getComingSoonModules } from "./lib/lary-data";

export default function Home() {
  const activeModules = getActiveModules();
  const comingSoonModules = getComingSoonModules();

  return (
    <PageShell>
      <section className="bg-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
          <div>
            <p className="text-base font-semibold uppercase tracking-wide text-blue-800">Модульный помощник для заявки ПФКИ</p>
            <h1 className="mt-4 max-w-4xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
              Соберите рабочие документы для заявки ПФКИ быстрее и без лишних ошибок
            </h1>
            <p className="mt-6 max-w-3xl text-xl leading-9 text-slate-700">
              Выберите задачу, ответьте на несколько вопросов и скачайте редактируемый DOCX или PPTX. По одному бесплатному запуску в каждом модуле.
            </p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <PrimaryLink href="/modules">Выбрать задачу</PrimaryLink>
              <SecondaryLink href="/#how-it-works">Как работает Лари</SecondaryLink>
            </div>
            <div className="mt-8 grid gap-3 text-base text-slate-700 sm:grid-cols-3">
              <div className="rounded-2xl bg-blue-50 p-4">Без регистрации до первого результата</div>
              <div className="rounded-2xl bg-green-50 p-4">Временные работы доступны 24 часа</div>
              <div className="rounded-2xl bg-slate-100 p-4">На выходе — рабочий редактируемый файл</div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-slate-50 p-5 shadow-sm">
            <div className="rounded-[1.5rem] bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Быстрый старт</p>
              <h2 className="mt-2 text-2xl font-bold">Что нужно сделать сегодня?</h2>
              <div className="mt-5 grid gap-3">
                {activeModules.slice(0, 4).map((module) => (
                  <Link key={module.slug} href={`/m/${module.slug}`} className="rounded-2xl border border-slate-200 p-4 text-left hover:border-blue-300 hover:bg-blue-50">
                    <span className="block text-lg font-bold text-slate-950">{module.taskTitle}</span>
                    <span className="mt-1 block text-sm text-slate-600">{module.outputFormats.join(" + ")} · {module.duration}</span>
                  </Link>
                ))}
              </div>
              <Link href="/modules" className="mt-5 inline-flex min-h-12 items-center justify-center rounded-2xl border border-blue-800 px-5 py-3 text-base font-semibold text-blue-900 hover:bg-blue-50">
                Показать все задачи
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Section eyebrow="Задачи" title="Закройте одну задачу по заявке - без сложной системы">
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {activeModules.map((module) => (
            <ModuleCard key={module.slug} module={module} />
          ))}
          {comingSoonModules.map((module) => (
            <ModuleCard key={module.slug} module={module} />
          ))}
        </div>
      </Section>

      <Section id="how-it-works" eyebrow="Как работает" title="Короткий путь к рабочему файлу" className="bg-white">
        <div className="grid gap-5 lg:grid-cols-4">
          {[
            ["1", "Выберите задачу", "Карточки говорят, что получится, сколько займет и какой файл будет на выходе."],
            ["2", "Заполните короткую форму", "4-7 основных полей, примеры, голосовой ввод в длинных описаниях."],
            ["3", "Проверьте подсказки", "Лари мягко укажет, если не хватает территории, целевой группы или цифр."],
            ["4", "Скачайте результат", "Рабочий редактируемый файл сразу, затем email, кабинет и проект — по желанию."],
          ].map(([step, title, text]) => (
            <div key={step} className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-800 text-lg font-bold text-white">{step}</span>
              <h3 className="mt-5 text-2xl font-bold">{title}</h3>
              <p className="mt-3 text-base leading-7 text-slate-700">{text}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Доверие" title="Серьезный сервис для официальной работы">
        <div className="grid gap-5 lg:grid-cols-3">
          <InfoCallout title="Не обещаем победу">
            Лари помогает подготовить рабочие документы, источники и черновики. Финальное решение по заявке остается за фондом.
          </InfoCallout>
          <InfoCallout tone="green" title="Не теряем результат">
            После запуска работу можно скачать сразу. Без email временный доступ сохраняется на 24 часа.
          </InfoCallout>
          <InfoCallout tone="orange" title="Не пугаем ошибками">
            Если сервис временно недоступен, пользователь видит понятное сообщение и знает, что данные сохранены.
          </InfoCallout>
        </div>
      </Section>

      <Section eyebrow="Состояния сервиса" title="Как выглядят загрузка, подсказки и ошибка">
        <ApiStatePanel />
      </Section>

      <Section eyebrow="Цены" title="Коммерческая логика простым языком" className="bg-white">
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 p-6">
            <p className="text-2xl font-bold">1 запуск модуля</p>
            <p className="mt-3 text-lg leading-8 text-slate-700">Одна генерация, расчет или сборка результата в любом доступном модуле.</p>
          </div>
          <div className="rounded-3xl border-2 border-blue-800 p-6">
            <p className="text-2xl font-bold">Пакет 6 запусков</p>
            <p className="mt-3 text-lg leading-8 text-slate-700">Удобно для подготовки комплекта материалов по заявке ПФКИ.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 p-6">
            <p className="text-2xl font-bold">Промокод</p>
            <p className="mt-3 text-lg leading-8 text-slate-700">Акции, партнерские коды и поддержка пользователей без сложных терминов.</p>
          </div>
        </div>
        <div className="mt-8">
          <PrimaryLink href="/pay">Посмотреть запуски</PrimaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
