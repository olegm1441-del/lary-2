export type ModuleRouteContext = {
  moduleSlug: string;
  contestSlug?: string | null;
  projectId?: string | null;
  mode?: string | null;
  example?: string | null;
  intent?: string | null;
  changeContest?: boolean;
  realExampleContests?: string[];
};

export function buildModuleRoute(context: ModuleRouteContext, targetContest?: string | null) {
  const params = new URLSearchParams();
  const contestSlug = targetContest ?? context.contestSlug;
  if (contestSlug) params.set("contest", contestSlug);
  if (context.projectId) params.set("project_id", context.projectId);

  const wantsExample = context.intent === "example" || context.example === "1";
  const wantsStart = context.intent === "start";
  if (targetContest) {
    if (wantsExample && context.realExampleContests?.includes(targetContest)) {
      params.set("example", "1");
    } else if (!wantsExample && (context.mode || wantsStart)) {
      params.set("mode", context.mode || "start");
    }
    if (context.intent) params.set("intent", context.intent);
  } else {
    if (context.mode || (contestSlug && wantsStart)) params.set("mode", context.mode || "start");
    if (context.example === "1" || (contestSlug && wantsExample && context.realExampleContests?.includes(contestSlug))) params.set("example", "1");
    if (context.intent) params.set("intent", context.intent);
    if (context.changeContest) params.set("change_contest", "1");
  }

  const query = params.toString();
  return `/m/${context.moduleSlug}${query ? `?${query}` : ""}`;
}
