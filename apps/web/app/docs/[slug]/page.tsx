import { notFound } from "next/navigation";
import { PageShell } from "../../components/lary-ui";
import { getLegalDocument, legalDocuments } from "../../lib/lary-data";
import { getLegalDocumentContent } from "../../data/legal-documents";

const fallbackLegalTexts: Record<string, Array<{ title: string; body: string[] }>> = {
  cookies: [
    {
      title: "1. Зачем нужны cookie",
      body: [
        "Cookie используются для временного кабинета, сохранения статуса работы, учета бесплатных попыток и согласий.",
        "Содержательные тексты заявки не хранятся в cookie.",
      ],
    },
    {
      title: "2. Управление cookie",
      body: [
        "Пользователь может ограничить cookie в настройках браузера, но временный кабинет и бесплатные попытки могут работать некорректно.",
      ],
    },
  ],
  conditions: [
    {
      title: "1. Условия оплаты",
      body: [
        "Пользователь покупает запуски модулей. Базовая цена одного запуска — 320 рублей.",
        "После оплаты или применения промокода пользователь возвращается к модулю с сохраненными введенными данными.",
      ],
    },
    {
      title: "2. Доставка результата",
      body: [
        "Результат предоставляется на сайте в виде скачиваемого DOCX, PDF или PPTX в зависимости от модуля.",
        "Без email результат доступен во временном кабинете ограниченное время.",
      ],
    },
    {
      title: "3. Возврат",
      body: [
        "При технической ошибке подготовки результата пользователь может повторить запуск без повторной оплаты или обратиться в поддержку.",
        "Вопросы по оплате и возвратам направляются на legacyinfo@yandex.ru.",
      ],
    },
  ],
};

type LegalBlock =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string };

export function generateStaticParams() {
  return legalDocuments.map((document) => ({ slug: document.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const document = getLegalDocument(slug);

  return {
    title: document ? `${document.title} — Лари` : "Документ Лари",
  };
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const document = getLegalDocument(slug);

  if (!document) notFound();

  const rawContent = getLegalDocumentContent(slug);
  const blocks = rawContent ? legalBlocksFromRawText(rawContent) : null;

  return (
    <PageShell>
      <section className="mx-auto w-full max-w-5xl overflow-hidden bg-white px-5 py-14 sm:px-8 lg:py-18">
        <p className="mb-3 text-base font-semibold uppercase tracking-wide text-blue-800">Юридический раздел</p>
        <h1 className="max-w-4xl break-words text-3xl font-bold tracking-tight text-slate-950 hyphens-auto [overflow-wrap:anywhere] sm:text-5xl">
          {document.title}
        </h1>
        <p className="mt-5 max-w-4xl break-words text-xl leading-9 text-slate-700 [overflow-wrap:anywhere]">{document.description}</p>

        {blocks ? (
          <article className="mt-10 grid max-w-4xl gap-6 break-words text-lg leading-8 text-slate-800 [overflow-wrap:anywhere]">
            {blocks.map((block, index) =>
              block.kind === "heading" ? (
                <h2 key={`${block.text}-${index}`} className="mt-4 break-words text-2xl font-bold leading-tight text-slate-950 [overflow-wrap:anywhere] sm:text-3xl">
                  {block.text}
                </h2>
              ) : (
                <p key={`${block.text}-${index}`} className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
                  {block.text}
                </p>
              ),
            )}
          </article>
        ) : (
          <div className="mt-8 grid max-w-4xl gap-8">
            {(fallbackLegalTexts[slug] || []).map((section) => (
              <section key={section.title} className="grid gap-4">
                <h2 className="break-words text-2xl font-bold text-slate-950 [overflow-wrap:anywhere]">{section.title}</h2>
                <div className="grid gap-3 break-words text-lg leading-8 text-slate-700 [overflow-wrap:anywhere]">
                  {section.body.map((paragraph) => (
                    <p key={paragraph} className="break-words [overflow-wrap:anywhere]">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </PageShell>
  );
}

function legalBlocksFromRawText(rawText: string): LegalBlock[] {
  const paragraphs = rawText
    .trim()
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  const contentParagraphs = stripDocumentHeader(paragraphs);

  return contentParagraphs.map((paragraph) => ({
    kind: isTopLevelHeading(paragraph) ? "heading" : "paragraph",
    text: paragraph,
  }));
}

function stripDocumentHeader(paragraphs: string[]) {
  if (paragraphs.length >= 3 && paragraphs[1] === "Лари / Lary.pro" && paragraphs[2].startsWith("Редакция от ")) {
    return paragraphs.slice(3);
  }
  if (paragraphs.length >= 2 && paragraphs[1].startsWith("Лари / Lary.pro\nРедакция от ")) {
    return paragraphs.slice(2);
  }
  return paragraphs;
}

function isTopLevelHeading(paragraph: string) {
  if (paragraph === "Реквизиты Администрации" || paragraph === "Реквизиты Администратора") return true;
  return /^\d+\.\s+\D/.test(paragraph);
}
