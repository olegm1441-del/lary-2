import modulesData from "../data/modules.json";
import { getPublicModules, getSupportedContests, type Contest } from "./product-registry";

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
  salary: ["region", "positions"],
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
  cofinance_source: ["Собственные средства юридического лица", "Привлеченные средства согласно письму поддержки"],
  cofunding: ["Собственные средства юридического лица", "Привлеченные средства согласно письму поддержки"],
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
  supportedContests: Contest[];
};

const legacyModules = modulesData as Omit<LaryModule, "supportedContests">[];
const productModules = new Map(getPublicModules().map((module) => [module.slug, module]));
export const modules = legacyModules.map((legacy) => {
  const product = productModules.get(legacy.slug);
  return {
    ...legacy,
    status: product?.status === "active" ? "active" : "coming_soon",
    taskTitle: product?.title || legacy.taskTitle,
    promise: product?.promise || legacy.promise,
    duration: product?.duration || legacy.duration,
    outputFormats: product?.output_formats || legacy.outputFormats,
    competition: "",
    supportedContests: getSupportedContests(legacy.slug),
  } satisfies LaryModule;
});

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
