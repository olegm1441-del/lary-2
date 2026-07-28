import { ModuleCard, PageShell, Section } from "../components/lary-ui";
import { getActiveModules, getComingSoonModules } from "../lib/lary-data";
import { buildModuleRoute } from "../lib/module-route";

export const metadata = {
  title: "Модули Лари",
};

export default async function ModulesPage({ searchParams }: { searchParams: Promise<{ project_id?: string; project_contest?: string }> }) {
  const query = await searchParams;
  const activeModules = getActiveModules();
  const comingSoonModules = getComingSoonModules();

  return (
    <PageShell>
      <Section eyebrow="Каталог задач" title="Что нужно подготовить для грантовой заявки?" className="bg-white">
        <div className="max-w-3xl text-xl leading-9 text-slate-700">
          Выберите задачу. Каждый запуск дает один рабочий файл или разбор.
        </div>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {activeModules.map((module) => (
            <ModuleCard key={module.slug} module={module} projectId={query.project_id} projectContest={query.project_contest} />
          ))}
        </div>
        <div className="mt-10 rounded-3xl border border-blue-100 bg-blue-50 p-6 text-blue-950">
          <h2 className="text-2xl font-bold">Не знаете, что выбрать?</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {[
              ["Нужно доказать проблему", "/m/social-research", "Доказательства актуальности"],
              ["Нужны законы и программы", "/m/legal-acts", "Нормативные акты"],
              ["Нужно обосновать расходы на команду", "/m/salary", "Зарплата"],
              ["Нужен документ от партнера", "/m/support-letter", "Письмо поддержки"],
              ["Нужно визуально показать проект", "/m/presentation", "Презентация"],
              ["Нужно описать мероприятие/постановку/ролик", "/m/scenario-plan", "Сценарный план"],
            ].map(([question, href, label]) => {
              const moduleSlug = href.replace("/m/", "");
              return (
              <a
                key={href}
                href={buildModuleRoute({
                  moduleSlug,
                  contestSlug: query.project_contest,
                  projectId: query.project_id,
                })}
                className="min-h-11 rounded-2xl bg-white px-4 py-3 text-base font-semibold text-blue-900 hover:bg-blue-100"
              >
                {question} → {label}
              </a>
              );
            })}
          </div>
        </div>
      </Section>

      <Section eyebrow="Дальше" title="Будущий модуль проверки заявки">
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {comingSoonModules.map((module) => (
            <ModuleCard key={module.slug} module={module} projectId={query.project_id} projectContest={query.project_contest} />
          ))}
        </div>
      </Section>
    </PageShell>
  );
}
