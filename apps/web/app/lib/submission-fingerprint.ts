type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

const TECHNICAL_KEYS = new Set(["ui_id", "_ui_id", "client_uuid", "expanded", "focused"]);

export function normalizeSubmissionPayload(value: unknown): JsonValue {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value.trim().replace(/\s+/g, " ");
  if (typeof value === "number" || typeof value === "boolean") return value;
  if (Array.isArray(value)) return value.map(normalizeSubmissionPayload);
  if (typeof value !== "object") return String(value);

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key]) => !TECHNICAL_KEYS.has(key))
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, nested]) => [key, normalizeSubmissionPayload(nested)]),
  );
}

export function stableSubmissionFingerprint(value: unknown) {
  return JSON.stringify(normalizeSubmissionPayload(value));
}
