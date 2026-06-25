import { InfoCallout, PageShell, PrimaryLink, Section } from "../components/lary-ui";

export const metadata = {
  title: "Помощь — Лари",
};

export default function HelpPage() {
  return (
    <PageShell>
      <Section eyebrow="Помощь" title="Если вы не знаете, с чего начать" className="bg-white">
        <div className="grid gap-5 lg:grid-cols-2">
          <InfoCallout title="Можно сделать проще">
            Выберите модуль, а Лари задаст вопросы по одному. В каждом большом поле можно написать коротко или использовать голосовой ввод после подключения speech API.
          </InfoCallout>
          <InfoCallout tone="orange" title="Если поле непонятно">
            Нажмите “Показать пример” или оставьте часть сведений на потом. Лари подскажет, какие данные действительно важны.
          </InfoCallout>
          <InfoCallout tone="green" title="Если результат нужен срочно">
            Начните с письма поддержки, расчета зарплаты или сценарного плана. Эти модули дают быстрый редактируемый файл.
          </InfoCallout>
          <InfoCallout tone="red" title="Если сервис не ответил">
            Данные сохранены. Попробуйте еще раз через минуту или напишите в поддержку с номером работы.
          </InfoCallout>
        </div>
        <div className="mt-8">
          <PrimaryLink href="/modules">Выбрать модуль</PrimaryLink>
        </div>
      </Section>
    </PageShell>
  );
}
