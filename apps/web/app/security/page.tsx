import { InfoCallout, PageShell, PrimaryLink, Section } from "../components/lary-ui";

export const metadata = {
  title: "Безопасность данных — Лари",
};

export default function SecurityPage() {
  return (
    <PageShell>
      <Section eyebrow="Безопасность" title="Что Лари хранит, зачем и как это удалить" className="bg-white">
        <p className="max-w-3xl text-xl leading-9 text-slate-700">
          Мы прямо объясняем, какие данные нужны для результата, сколько они хранятся и как удалить работу.
        </p>
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          <InfoCallout title="Что собираем">
            Ответы в формах, технический идентификатор временной сессии, статус запуска, тип и размер файла.
          </InfoCallout>
          <InfoCallout tone="green" title="Зачем">
            Чтобы подготовить рабочий файл, сохранить черновик, показать результат и учесть бесплатные или оплаченные запуски.
          </InfoCallout>
          <InfoCallout tone="orange" title="Срок хранения">
            Работы без email временно доступны 24 часа в этом браузере. В cookie не сохраняются тексты заявки и файлы.
          </InfoCallout>
          <InfoCallout title="Файлы и голос">
            Файлы нужны для скачивания результата. Аудио используется только для перевода речи в текст: перед запуском его можно исправить.
          </InfoCallout>
          <InfoCallout tone="green" title="Кто имеет доступ">
            Доступ к данным ограничен техническими задачами сервиса и поддержкой пользователя по его обращению.
          </InfoCallout>
          <InfoCallout tone="orange" title="Как удалить">
            Удалить работу можно в личном кабинете или через обращение в поддержку. В обращении не нужно отправлять пароли и лишние персональные данные.
          </InfoCallout>
          <InfoCallout title="Что не пишется в логи">
            В технические логи не пишутся полные тексты заявок, содержимое файлов, email в открытом виде, ключи и секреты.
          </InfoCallout>
        </div>
        <div className="mt-8">
          <PrimaryLink href="/docs/privacy">Открыть политику</PrimaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
