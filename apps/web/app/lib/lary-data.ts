import modulesData from "../data/modules.json";

export type ModuleStatus = "active" | "coming_soon";

export type ModuleField = {
  label: string;
  type: string;
  required: boolean;
  example: string;
  hint: string;
};

export const FIELD_KEYS_BY_MODULE: Record<string, string[]> = {
  "social-research": ["region", "direction", "target_group", "problem", "details"],
  "legal-acts": ["program_level", "region", "direction", "target_group", "details"],
  salary: ["role", "region", "functionality", "months", "employee_count", "employment_percent", "employment_hours", "calendar_items", "cofunding"],
  "support-letter": [
    "contest",
    "project_title",
    "partner_name",
    "partner_intro_block",
    "value_keywords",
    "support_types",
    "support_details",
    "cofinance_block",
    "signatory",
  ],
  presentation: ["project_description", "visual_style", "slide_count", "calendar_plan", "details"],
  "scenario-plan": ["scenario_type", "description", "duration", "preparation", "participants", "details"],
  "check-application": ["file", "competition", "focus_sections", "email"],
};

export const FIELD_OPTIONS_BY_KEY: Record<string, string[]> = {
  region: ["Республика Татарстан", "Свердловская область", "Москва", "Санкт-Петербург", "Краснодарский край", "Нижегородская область"],
  direction: ["Дворовой футбол", "Театр", "Музей", "Семейная память", "Локальная история", "Культурный фестиваль", "Спорт и культура"],
  program_level: ["Федеральные и региональные документы", "Только федеральные документы", "Только региональные документы"],
  role: ["Координатор проекта", "Организатор", "Куратор", "Режиссер", "Методист", "SMM-специалист"],
  cofunding: ["Собственные средства", "Письмо поддержки", "Имущественный вклад", "Без софинансирования"],
  support_types: [
    "Информационная",
    "Консультационная",
    "Организационная",
    "Материальная",
    "Финансовая",
    "Иная",
  ],
  contest: ["ПФКИ"],
  competition: ["ПФКИ", "Фонд президентских грантов", "Движение Первых", "Региональный конкурс"],
  scenario_type: [
    "Фестиваль",
    "Концерт",
    "Постановка/спектакль",
    "Видео/ролик",
    "Документальный фильм",
    "Выставка",
    "Форум/конференция",
    "Мастер-класс/лаборатория",
    "Конкурс/премия",
    "Спортивно-культурное событие",
  ],
  visual_style: ["Официальный", "Минималистичный"],
  slide_count: ["6–8", "10–12 рекомендуется", "13–15", "Лари выберет"],
};

export type LaryModule = {
  slug: string;
  status: ModuleStatus;
  title: string;
  shortTitle: string;
  taskTitle: string;
  promise: string;
  duration: string;
  freeAttempt: string;
  competition: string;
  outputFormats: string[];
  accent: string;
  stage: string;
  fields: ModuleField[];
  aiHints: string[];
  resultPreview: string[];
  resultActions: string[];
};

export const modules = modulesData as LaryModule[];

export function getActiveModules() {
  return modules.filter((module) => module.status === "active");
}

export function getComingSoonModules() {
  return modules.filter((module) => module.status === "coming_soon");
}

export function getModuleBySlug(slug: string) {
  return modules.find((module) => module.slug === slug);
}

export function getModuleSlugs() {
  return modules.map((module) => module.slug);
}

export function getFieldKey(moduleSlug: string, fieldIndex: number, label: string) {
  return FIELD_KEYS_BY_MODULE[moduleSlug]?.[fieldIndex] || label.toLowerCase().replace(/\s+/g, "_");
}

export function getFieldOptions(fieldKey: string) {
  return FIELD_OPTIONS_BY_KEY[fieldKey] || [];
}

export const legalDocuments = [
  {
    slug: "privacy",
    title: "Политика конфиденциальности и обработки персональных данных",
    description: "Лари / Lary.pro · редакция от 26.06.2026",
  },
  {
    slug: "agreement",
    title: "Пользовательское соглашение",
    description: "Лари / Lary.pro · редакция от 26.06.2026",
  },
  {
    slug: "cookies",
    title: "Политика cookie",
    description: "Как работает временный кабинет, бесплатные попытки и технические идентификаторы.",
  },
  {
    slug: "offer",
    title: "Публичная оферта",
    description: "Лари / Lary.pro · редакция от 26.06.2026",
  },
  {
    slug: "conditions",
    title: "Условия оплаты, доставки и возврата",
    description: "Как оплачиваются запуски модулей и что делать при ошибке платежа.",
  },
];

export function getLegalDocument(slug: string) {
  return legalDocuments.find((document) => document.slug === slug);
}
