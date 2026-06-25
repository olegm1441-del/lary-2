export const MODULE_ATTEMPTS_STORAGE_KEY = "lary.module_attempts.v1";
export const MODULE_ATTEMPT_USED_EVENT = "lary-module-attempt-used";

export function getUsedModuleAttempts() {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(MODULE_ATTEMPTS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

export function isModuleAttemptUsed(moduleSlug: string) {
  return getUsedModuleAttempts().includes(moduleSlug);
}

export function markModuleAttemptUsed(moduleSlug: string) {
  if (typeof window === "undefined") return;
  const used = new Set(getUsedModuleAttempts());
  used.add(moduleSlug);
  window.localStorage.setItem(MODULE_ATTEMPTS_STORAGE_KEY, JSON.stringify([...used]));
  window.dispatchEvent(new CustomEvent(MODULE_ATTEMPT_USED_EVENT, { detail: { moduleSlug } }));
}
