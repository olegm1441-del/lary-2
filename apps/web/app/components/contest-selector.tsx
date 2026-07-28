"use client";

import Link from "next/link";
import type { Contest } from "../lib/product-registry";
import { buildModuleRoute } from "../lib/module-route";

export function ContestSelector({
  contests,
  moduleSlug,
  selected,
  projectId,
  mode,
  example,
  intent,
  realExampleContests = [],
}: {
  contests: Contest[];
  moduleSlug: string;
  selected?: string | null;
  projectId?: string | null;
  mode?: string | null;
  example?: string | null;
  intent?: string | null;
  realExampleContests?: string[];
}) {
  return (
    <section id="contest" className="rounded-3xl border border-blue-200 bg-blue-50 p-5 sm:p-6">
      <h2 className="text-3xl font-bold text-slate-950">Выберите конкурс</h2>
      <p className="mt-3 text-lg leading-8 text-slate-700">
        Лари подстроит вопросы, подсказки и результат под требования конкурса.
      </p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Конкурс">
        {contests.map((contest) => (
          <Link
            key={contest.slug}
            href={buildModuleRoute(
              {
                moduleSlug,
                projectId,
                mode,
                example,
                intent,
                realExampleContests,
              },
              contest.slug,
            )}
            role="radio"
            aria-checked={selected === contest.slug}
            className={`flex min-h-14 items-center rounded-2xl border px-5 py-4 text-lg font-semibold focus:outline-none focus:ring-2 focus:ring-blue-700 ${
              selected === contest.slug
                ? "border-blue-800 bg-white text-blue-950"
                : "border-blue-200 bg-white/70 text-slate-900 hover:border-blue-500"
            }`}
          >
            {contest.name}
          </Link>
        ))}
      </div>
    </section>
  );
}
