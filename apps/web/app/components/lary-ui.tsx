import Link from "next/link";
import { MobileMenu } from "./mobile-menu";
import { ModuleAttemptStatus } from "./module-attempt-status";
import type { LaryModule, ModuleField } from "../lib/lary-data";
import { ContestChips } from "./contest-chips";
import { RunBalance } from "./run-balance";
import { hasRealExample } from "../lib/product-registry";
import { getPublicContests } from "../lib/product-registry";
import { buildModuleRoute } from "../lib/module-route";

const navItems = [
  { label: "Модули", href: "/modules" },
  { label: "Как работает", href: "/#how-it-works" },
  { label: "Цены", href: "/pay" },
  { label: "Безопасность", href: "/security" },
  { label: "Помощь", href: "/help" },
];

const mobileNavItems = [...navItems, { label: "Войти", href: "/account" }];

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-20 w-full max-w-7xl items-center justify-between gap-3 px-5 py-3 sm:gap-5 sm:px-8">
        <Link href="/" className="flex min-w-0 items-center gap-3 text-slate-950" aria-label="Лари — на главную">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-800 text-xl font-bold text-white">
            L
          </span>
          <span className="min-w-0 max-[500px]:hidden">
            <span className="block text-2xl font-bold leading-6">Лари</span>
            <span className="block truncate text-sm text-slate-500 max-[640px]:hidden">AI-помощник по составлению грантовых заявок</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-5 text-base font-medium text-slate-700 lg:flex" aria-label="Основная навигация">
          {navItems.map(({ label, href }) => (
            <Link key={href} href={href} className="inline-flex min-h-11 items-center rounded-xl px-2 py-2 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-700">
              {label}
            </Link>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-3">
          <RunBalance />
          <MobileMenu items={mobileNavItems} />
          <Link href="/account" className="hidden rounded-2xl px-4 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-700 sm:inline-flex">
            Войти
          </Link>
          <Link href="/modules" className="hidden rounded-2xl bg-blue-800 px-4 py-3 text-base font-semibold text-white shadow-sm hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2 sm:inline-flex sm:px-5">
            Начать
          </Link>
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-950 text-slate-100">
      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-10 sm:px-8 lg:grid-cols-[1.3fr_1fr_1fr_1fr]">
        <div>
          <p className="text-2xl font-bold">Лари</p>
          <p className="mt-3 max-w-xl text-base leading-7 text-slate-300">
            Лари — AI-помощник по составлению грантовых заявок. Сервис помогает собрать рабочие документы, но не обещает победу в конкурсе.
          </p>
          <div className="mt-5 text-sm leading-6 text-slate-400">
            <p>ИП Сумин Александр Николаевич</p>
            <p>г. Екатеринбург, ул. Сыромолотова 14, оф. 600</p>
            <p>ОГРНИП: 315665800076101 · ИНН: 667005585512</p>
            <p>E-mail: legacyinfo@yandex.ru</p>
          </div>
        </div>
        <div>
          <p className="font-semibold">Разделы</p>
          <div className="mt-3 grid gap-2 text-slate-300">
            <Link href="/modules" className="inline-flex min-h-11 items-center">Модули</Link>
            <Link href="/security" className="inline-flex min-h-11 items-center">Безопасность</Link>
            <Link href="/help" className="inline-flex min-h-11 items-center">Помощь</Link>
            <Link href="/contacts" className="inline-flex min-h-11 items-center">Контакты</Link>
          </div>
        </div>
        <div>
          <p className="font-semibold">Документы</p>
          <div className="mt-3 grid gap-2 text-slate-300">
            <Link href="/docs/privacy" className="inline-flex min-h-11 items-center">Политика персональных данных</Link>
            <Link href="/docs/agreement" className="inline-flex min-h-11 items-center">Пользовательское соглашение</Link>
            <Link href="/docs/offer" className="inline-flex min-h-11 items-center">Публичная оферта</Link>
            <Link href="/docs/cookies" className="inline-flex min-h-11 items-center">Политика cookie</Link>
            <Link href="/docs/conditions" className="inline-flex min-h-11 items-center">Оплата и возврат</Link>
          </div>
        </div>
        <div>
          <p className="font-semibold">Важно</p>
          <p className="mt-3 text-base leading-7 text-slate-300">
            Аудио используется только для распознавания речи. Работы без email временно доступны 24 часа. Перед подачей документы нужно проверить вручную.
          </p>
        </div>
      </div>
    </footer>
  );
}

export function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <Header />
      <main>{children}</main>
      <Footer />
    </div>
  );
}

export function Section({ eyebrow, title, children, className = "", id }: { eyebrow?: string; title: string; children: React.ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={`mx-auto w-full max-w-7xl overflow-hidden px-5 py-14 sm:px-8 lg:py-18 ${className}`}>
      {eyebrow ? <p className="mb-3 text-base font-semibold uppercase tracking-wide text-blue-800">{eyebrow}</p> : null}
      <h2 className="max-w-4xl break-words text-3xl font-bold tracking-tight text-slate-950 hyphens-auto sm:text-4xl">{title}</h2>
      <div className="mt-8">{children}</div>
    </section>
  );
}

export function ModuleCard({ module, compact = false, projectId, projectContest }: { module: LaryModule; compact?: boolean; projectId?: string; projectContest?: string }) {
  const href = buildModuleRoute({
    moduleSlug: module.slug,
    contestSlug: projectContest,
    projectId,
  });
  const hasContextExample = projectContest ? hasRealExample(module.slug, projectContest) : false;
  const hasAnyExample = getPublicContests().some((contest) => hasRealExample(module.slug, contest.slug));
  const exampleHref = projectContest
    ? buildModuleRoute({ moduleSlug: module.slug, contestSlug: projectContest, projectId, example: "1" })
    : buildModuleRoute({ moduleSlug: module.slug, projectId, intent: "example" });

  return (
    <article className="group flex h-full min-w-0 max-w-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-800">{module.stage}</p>
          <h3 className="mt-2 break-words text-2xl font-bold text-slate-950">{module.taskTitle}</h3>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${module.status === "active" ? "bg-green-50 text-green-800" : "bg-orange-50 text-orange-800"}`}>
          {module.status === "active" ? "Доступно" : "Скоро"}
        </span>
      </div>
      <p className="mt-4 break-words text-lg leading-8 text-slate-700">{module.promise}</p>
      <p className="mt-3 text-base font-semibold text-slate-600">Результат можно скачать и доработать вручную.</p>
      <div className="mt-5 flex flex-wrap gap-2">
        <Badge>{module.duration}</Badge>
        <Badge>{module.outputFormats.join(" + ")}</Badge>
      </div>
      <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Подходит для</p>
      <ContestChips contests={module.supportedContests} />
      {!compact && module.status === "active" ? <ModuleAttemptStatus moduleSlug={module.slug} /> : null}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <Link
          href={href}
          className="inline-flex min-h-12 w-full items-center justify-center whitespace-normal rounded-2xl bg-blue-800 px-5 py-3 text-center text-base font-semibold text-white group-hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2"
        >
          {module.status === "active" ? "Начать" : "Посмотреть"}
        </Link>
        {module.status === "active" && (projectContest ? hasContextExample : hasAnyExample) ? (
          <Link
            href={exampleHref}
            className="inline-flex min-h-12 w-full items-center justify-center whitespace-normal rounded-2xl border border-slate-300 bg-white px-5 py-3 text-center text-base font-semibold text-slate-900 hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2"
          >
            Посмотреть пример
          </Link>
        ) : module.status === "active" ? (
          <span className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-slate-200 px-5 py-3 text-center text-sm font-semibold text-slate-500">
            Пример для этого конкурса пока готовится
          </span>
        ) : null}
      </div>
    </article>
  );
}

export function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">{children}</span>;
}

export function InfoCallout({ tone = "blue", title, children }: { tone?: "blue" | "green" | "orange" | "red"; title: string; children: React.ReactNode }) {
  const colors = {
    blue: "border-blue-200 bg-blue-50 text-blue-950",
    green: "border-green-200 bg-green-50 text-green-950",
    orange: "border-orange-200 bg-orange-50 text-orange-950",
    red: "border-red-200 bg-red-50 text-red-950",
  };

  return (
    <div className={`rounded-3xl border p-5 ${colors[tone]}`}>
      <p className="text-lg font-bold">{title}</p>
      <div className="mt-2 text-base leading-7">{children}</div>
    </div>
  );
}

export function FieldPreview({ field }: { field: ModuleField }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-lg font-bold text-slate-950">{field.label}</p>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${field.required ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-600"}`}>
          {field.required ? "обязательно" : "можно позже"}
        </span>
      </div>
      <p className="mt-3 text-base text-slate-600">{field.hint}</p>
      <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-base text-slate-500">
        Например: {field.example}
      </div>
    </div>
  );
}

export function ApiStatePanel() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <InfoCallout title="Подготовка результата">
        Данные сохранены. Лари готовит ответ и покажет понятный статус, если обработка займет больше обычного.
      </InfoCallout>
      <InfoCallout tone="orange" title="Если данных мало">
        Лари мягко подскажет, что уточнить: территорию, целевую группу, вклад партнера или параметры расчета.
      </InfoCallout>
      <InfoCallout tone="red" title="Если сервис временно недоступен">
        Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту или напишите в поддержку.
      </InfoCallout>
    </div>
  );
}

export function WorkPanel({ module, contestName = "Конкурс не выбран" }: { module: LaryModule; contestName?: string }) {
  return (
    <aside className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-28">
      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Моя работа</p>
      <div className="mt-4 grid gap-4 text-base">
        <div>
          <p className="text-slate-500">Конкурс</p>
          <p className="font-bold text-green-800">{contestName}</p>
        </div>
        <div>
          <p className="text-slate-500">Результат</p>
          <p className="font-bold">{module.outputFormats.join(" + ")}</p>
        </div>
        <div>
          <p className="text-slate-500">Черновик</p>
          <p className="font-bold text-blue-800">сохраняется автоматически</p>
        </div>
      </div>
    </aside>
  );
}

export function PrimaryLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="inline-flex min-h-14 items-center justify-center rounded-2xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2">
      {children}
    </Link>
  );
}

export function SecondaryLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-slate-300 bg-white px-6 py-4 text-lg font-semibold text-slate-900 hover:border-blue-300 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-700 focus:ring-offset-2">
      {children}
    </Link>
  );
}
