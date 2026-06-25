import { InfoCallout, PageShell, PrimaryLink, Section } from "../components/lary-ui";
import { PaymentPanel } from "../components/payment-panel";

export const metadata = {
  title: "Запуски модулей — Лари",
};

export default function PayPage() {
  return (
    <PageShell>
      <Section eyebrow="Оплата" title="Купить запуск модуля или применить промокод" className="bg-white">
        <p className="max-w-3xl text-xl leading-9 text-slate-700">
          Один запуск — это одна генерация, расчет или сборка результата в любом доступном модуле. Оплата не должна сбрасывать заполненную форму.
        </p>
        <PaymentPanel />
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <InfoCallout tone="green" title="После успешной оплаты">
            Пользователь возвращается в тот же модуль с сохраненными данными. Запуск начисляется один раз.
          </InfoCallout>
          <InfoCallout tone="red" title="Если платеж не прошел">
            Оплата не прошла. Деньги не списаны или платеж не подтвержден. Попробуйте еще раз или напишите в поддержку.
          </InfoCallout>
        </div>
        <div className="mt-8">
          <PrimaryLink href="/modules">Вернуться к модулям</PrimaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
