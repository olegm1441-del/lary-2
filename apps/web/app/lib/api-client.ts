const DEFAULT_API_URL = "http://127.0.0.1:8000";

export function apiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/$/, "");
}

export function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl()}${normalizedPath}`;
}

export async function readApiError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (typeof payload?.detail?.message === "string") return payload.detail.message;
    if (typeof payload?.message === "string") return payload.message;
  } catch {
    return "Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту.";
  }
  return "Не получилось подготовить ответ. Данные сохранены. Попробуйте еще раз через минуту.";
}
