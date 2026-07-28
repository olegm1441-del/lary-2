export function moduleDraftKey(moduleSlug: string, contestSlug: string, projectId?: string | null) {
  return `lary:draft:v2:${moduleSlug}:${contestSlug}:${projectId || "anonymous"}`;
}

export function moduleResultStateKey(moduleSlug: string, contestSlug: string, projectId?: string | null) {
  return `lary:result-state:v1:${moduleSlug}:${contestSlug}:${projectId || "anonymous"}`;
}

export function migrateLegacyDraft<T>(
  storage: Pick<Storage, "getItem" | "setItem" | "removeItem">,
  moduleSlug: string,
  contestSlug: string,
  projectId?: string | null,
): T | null {
  const nextKey = moduleDraftKey(moduleSlug, contestSlug, projectId);
  const existing = storage.getItem(nextKey);
  if (existing) return safeParse<T>(existing);
  if (contestSlug !== "pfki") return null;

  const legacyKeys = [
    `lary.module_draft.${moduleSlug}`,
    moduleSlug === "salary" ? "lary.module_draft.salary.v2" : "",
  ].filter(Boolean);
  for (const legacyKey of legacyKeys) {
    const legacy = storage.getItem(legacyKey);
    if (!legacy) continue;
    storage.setItem(nextKey, legacy);
    storage.removeItem(legacyKey);
    return safeParse<T>(legacy);
  }
  return null;
}

function safeParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}
