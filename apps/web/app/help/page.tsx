import { InfoCallout, PageShell, PrimaryLink, Section, SecondaryLink } from "../components/lary-ui";

export const metadata = {
  title: "Помощь — Лари",
};

const categories = [
  ["Начало работы", "Выберите задачу, заполните короткую форму и скачайте рабочий редактируемый файл."],
  ["Модули", "Каждый модуль закрывает одну прикладную задачу: НПА, актуальность, зарплата, письмо, презентация или сценарий."],
  ["Оплата и промокоды", "Повторный запуск требует один запуск модуля. Промокод можно применить на странице оплаты."],
  ["Мои работы", "Без email работа доступна 24 часа в этом браузере. Email нужен, чтобы сохранить ее надолго."],
  ["Файлы и проекты", "После результата работу можно скачать, отправить на почту или прикрепить к проекту."],
  ["Безопасность", "В cookie не сохраняются тексты заявки и файлы. Аудио используется только для распознавания речи."],
  ["Ошибки", "Если результат не подготовился, данные сохранены. Попробуйте еще раз через минуту или напишите в поддержку."],
];

export default function HelpPage() {
  return (
    <PageShell>
      <Section eyebrow="Помощь" title="Что хотите узнать?" className="bg-white">
        <label className="block max-w-3xl">
          <span className="text-lg font-semibold text-slate-950">Поиск по помощи</span>
          <input
            type="search"
            placeholder="Например: промокод, файл, временная работа"
            className="mt-3 min-h-14 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
          />
        </label>

        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          {categories.map(([title, text]) => (
            <InfoCallout key={title} title={title}>
              <p>{text}</p>
            </InfoCallout>
          ))}
        </div>

        <div className="mt-8 flex flex-col gap-4 sm:flex-row">
          <PrimaryLink href="/modules">Перейти к задачам</PrimaryLink>
          <SecondaryLink href="/contacts">Написать в поддержку</SecondaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
