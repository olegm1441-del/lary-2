import { notFound } from "next/navigation";
import { InfoCallout, PageShell, Section } from "../../components/lary-ui";
import { getLegalDocument, legalDocuments } from "../../lib/lary-data";

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

  return (
    <PageShell>
      <Section eyebrow="Юридический раздел" title={document.title} className="bg-white">
        <p className="max-w-3xl text-xl leading-9 text-slate-700">{document.description}</p>
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <InfoCallout title="Что нужно раскрыть в финальной версии">
            Цели обработки, срок хранения временных работ, аудио для распознавания, файлы, email, cookie, оплата, промокоды и право удалить данные.
          </InfoCallout>
          <InfoCallout tone="orange" title="Статус MVP">
            Это продуктовая заготовка страницы. Перед публикацией на домене текст должен пройти юридическую проверку.
          </InfoCallout>
        </div>
      </Section>
    </PageShell>
  );
}
