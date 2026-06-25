import { InfoCallout, PageShell, PrimaryLink, Section } from "../components/lary-ui";

export const metadata = {
  title: "Безопасность данных — Лари",
};

export default function SecurityPage() {
  return (
    <PageShell>
      <Section eyebrow="Безопасность" title="Что Лари хранит, зачем и как это объясняется пользователю" className="bg-white">
        <p className="max-w-3xl text-xl leading-9 text-slate-700">
          Нельзя обещать абсолютную безопасность. Нужно прямо объяснять, какие данные нужны для результата, сколько они хранятся и как их удалить.
        </p>
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          <InfoCallout title="До результата">
            Текстовые поля, техническая сессия и обезличенные события нужны, чтобы подготовить результат и не потерять черновик.
          </InfoCallout>
          <InfoCallout tone="green" title="Временный кабинет">
            Результаты без email доступны 24 часа через технический идентификатор. Содержательные данные не хранятся в cookie.
          </InfoCallout>
          <InfoCallout tone="orange" title="Логи">
            В технические логи не пишутся полные тексты заявок, файлы, персональные данные, полные AI-ответы, ключи и секреты.
          </InfoCallout>
        </div>
        <div className="mt-8">
          <PrimaryLink href="/docs/privacy">Открыть политику</PrimaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
