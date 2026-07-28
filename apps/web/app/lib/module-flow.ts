export const MODULE_RESULT_READY_EVENT = "lari:module-result-ready";

export type ModuleResultReadyDetail = {
  moduleSlug: string;
  resultId: string;
};

export function emitModuleResultReady(moduleSlug: string, resultId: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<ModuleResultReadyDetail>(MODULE_RESULT_READY_EVENT, {
      detail: { moduleSlug, resultId },
    }),
  );
}
