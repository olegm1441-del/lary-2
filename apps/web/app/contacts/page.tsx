import { InfoCallout, PageShell, Section } from "../components/lary-ui";

export const metadata = {
  title: "Контакты — Лари",
};

export default function ContactsPage() {
  return (
    <PageShell>
      <Section eyebrow="Контакты" title="Связаться с командой Лари" className="bg-white">
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <p className="text-2xl font-bold">Почта</p>
            <p className="mt-3 text-lg text-slate-700">legacyinfo@yandex.ru</p>
            <p className="mt-6 text-2xl font-bold">Юридическая информация</p>
            <p className="mt-3 text-lg leading-8 text-slate-700">
              ИП Сумин Александр Николаевич. ИНН: 667005585512. ОГРНИП: 315665800076101.
            </p>
          </div>
          <InfoCallout title="Что писать в поддержку">
            Укажите email, модуль, примерное время запуска и номер работы, если он есть. Не отправляйте лишние персональные данные.
          </InfoCallout>
        </div>
      </Section>
    </PageShell>
  );
}
