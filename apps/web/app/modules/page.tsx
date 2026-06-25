import { ModuleCard, PageShell, Section } from "../components/lary-ui";
import { getActiveModules, getComingSoonModules } from "../lib/lary-data";

export const metadata = {
  title: "Модули Лари",
};

export default function ModulesPage() {
  const activeModules = getActiveModules();
  const comingSoonModules = getComingSoonModules();

  return (
    <PageShell>
      <Section eyebrow="Каталог задач" title="Что нужно подготовить для заявки ПФКИ?" className="bg-white">
        <div className="max-w-3xl text-xl leading-9 text-slate-700">
          Выберите задачу. Каждый запуск дает один рабочий файл или разбор.
        </div>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {activeModules.map((module) => (
            <ModuleCard key={module.slug} module={module} />
          ))}
        </div>
      </Section>

      <Section eyebrow="Дальше" title="Будущий модуль проверки заявки">
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {comingSoonModules.map((module) => (
            <ModuleCard key={module.slug} module={module} />
          ))}
        </div>
      </Section>
    </PageShell>
  );
}
