import modulesData from "../data/modules.json";

export type ModuleStatus = "active" | "coming_soon";

export type ModuleField = {
  label: string;
  type: string;
  required: boolean;
  example: string;
  hint: string;
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

export const legalDocuments = [
  {
    slug: "privacy",
    title: "Политика обработки персональных данных",
    description: "Что собираем, зачем, сколько храним и как удалить данные.",
  },
  {
    slug: "agreement",
    title: "Пользовательское соглашение",
    description: "Правила использования Лари, модулей, результатов и личного кабинета.",
  },
  {
    slug: "cookies",
    title: "Политика cookie",
    description: "Как работает временный кабинет, бесплатные попытки и технические идентификаторы.",
  },
  {
    slug: "offer",
    title: "Публичная оферта",
    description: "Покупка запусков модулей, промокоды, возвраты и ограничения ответственности.",
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
