"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiUrl, readApiError } from "../lib/api-client";
import { moduleDraftKey } from "../lib/module-drafts";
import { buildModuleRoute } from "../lib/module-route";

type ProjectItem = {
  project_id: string;
  contest_slug?: string | null;
};

export function ProjectContestSync({
  moduleSlug,
  projectId,
  selectedContest,
  mode,
  example,
  intent,
  changeContest,
  realExampleContests,
}: {
  moduleSlug: string;
  projectId?: string | null;
  selectedContest?: string | null;
  mode?: string | null;
  example?: string | null;
  intent?: string | null;
  changeContest?: boolean;
  realExampleContests: string[];
}) {
  const router = useRouter();

  useEffect(() => {
    if (!projectId) return;
    const stableProjectId = projectId;
    let cancelled = false;

    async function synchronize() {
      const response = await fetch(apiUrl("/api/projects"), {
        credentials: "include",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = (await response.json()) as { items?: ProjectItem[] };
      const project = payload.items?.find((item) => item.project_id === stableProjectId);
      if (!project?.contest_slug || cancelled) return;

      if (!selectedContest && !changeContest) {
        router.replace(
          buildModuleRoute(
            {
              moduleSlug,
              projectId: stableProjectId,
              mode,
              example,
              intent,
              realExampleContests,
            },
            project.contest_slug,
          ),
        );
        return;
      }

      if (selectedContest && selectedContest !== project.contest_slug) {
        const previousDraft = window.localStorage.getItem(
          moduleDraftKey(moduleSlug, project.contest_slug, stableProjectId),
        );
        let hasIncompatibleDraft = false;
        if (previousDraft) {
          try {
            const parsed = JSON.parse(previousDraft) as unknown;
            hasIncompatibleDraft =
              typeof parsed === "object" &&
              parsed !== null &&
              Object.keys(parsed as Record<string, unknown>).length > 0;
          } catch {
            hasIncompatibleDraft = true;
          }
        }
        if (
          hasIncompatibleDraft &&
          !window.confirm(
            "В проекте есть черновик для прежнего конкурса. Переключить конкурс? Черновик сохранится и восстановится при возврате.",
          )
        ) {
          router.replace(
            buildModuleRoute({
              moduleSlug,
              contestSlug: project.contest_slug,
              projectId: stableProjectId,
              mode,
              example,
              intent,
              realExampleContests,
            }),
          );
          return;
        }
        const updateResponse = await fetch(apiUrl(`/api/projects/${encodeURIComponent(stableProjectId)}`), {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contest_slug: selectedContest }),
        });
        if (!updateResponse.ok) throw new Error(await readApiError(updateResponse));
      }
    }

    void synchronize().catch(() => {
      // The selector remains usable when a stale or inaccessible project id is supplied.
    });
    return () => {
      cancelled = true;
    };
  }, [
    changeContest,
    example,
    intent,
    mode,
    moduleSlug,
    projectId,
    realExampleContests,
    router,
    selectedContest,
  ]);

  return null;
}
