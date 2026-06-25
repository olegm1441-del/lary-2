import { InfoCallout, PageShell, PrimaryLink, Section } from "../components/lary-ui";

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
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 p-6">
            <p className="text-3xl font-bold">1 запуск</p>
            <p className="mt-4 text-lg leading-8 text-slate-700">Для повторного запуска одного модуля или быстрой проверки идеи.</p>
            <button className="mt-6 min-h-14 w-full rounded-2xl bg-blue-800 px-5 py-4 text-lg font-semibold text-white">Купить 1 запуск</button>
          </div>
          <div className="rounded-3xl border-2 border-blue-800 p-6">
            <p className="text-3xl font-bold">6 запусков</p>
            <p className="mt-4 text-lg leading-8 text-slate-700">Пакет под все шесть MVP-модулей или несколько попыток в нужном модуле.</p>
            <button className="mt-6 min-h-14 w-full rounded-2xl bg-blue-800 px-5 py-4 text-lg font-semibold text-white">Купить пакет</button>
          </div>
          <div className="rounded-3xl border border-slate-200 p-6">
            <p className="text-3xl font-bold">Промокод</p>
            <p className="mt-4 text-lg leading-8 text-slate-700">Введите код, чтобы получить бесплатные или дополнительные запуски.</p>
            <div className="mt-6 rounded-2xl border border-slate-300 bg-slate-50 p-4 text-slate-500">Например: LARY-START</div>
          </div>
        </div>
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
