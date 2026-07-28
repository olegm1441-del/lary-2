"use client";

export type FieldAssistantStatus = "info" | "warning" | "error" | "success";

export type FieldAssistantSuggestion = {
  id: string;
  label: string;
  operation: "suggest_text" | "dismiss";
  text: string;
};

export type FieldAssistantHintData = {
  status: FieldAssistantStatus;
  should_block: boolean;
  message: string;
  suggestions?: FieldAssistantSuggestion[];
  covered_by_fields?: string[];
  rewrite_suggestion?: string | null;
};

const toneClasses: Record<FieldAssistantStatus, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-950",
  warning: "border-orange-200 bg-orange-50 text-orange-950",
  error: "border-red-200 bg-red-50 text-red-950",
  success: "border-green-200 bg-green-50 text-green-950",
};

export function FieldAssistantHint({
  hint,
  onSuggestion,
}: {
  hint?: FieldAssistantHintData | null;
  onSuggestion?: (suggestion: FieldAssistantSuggestion) => void;
}) {
  if (!hint?.message || hint.status === "success") return null;

  return (
    <div className={`mt-3 max-w-full rounded-2xl border p-3 text-base leading-7 break-words [overflow-wrap:anywhere] ${toneClasses[hint.status]}`}>
      <p className="max-w-full break-words [overflow-wrap:anywhere]">{hint.message}</p>
      {hint.suggestions?.length ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {hint.suggestions.slice(0, 3).map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              onClick={() => onSuggestion?.(suggestion)}
              className="min-h-10 max-w-full whitespace-normal break-words rounded-xl border border-current/20 bg-white/70 px-3 py-2 text-left text-sm font-semibold [overflow-wrap:anywhere] hover:bg-white"
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
