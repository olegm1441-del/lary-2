import { InfoCallout, PageShell, Section } from "../components/lary-ui";
import { AccountWorkspace } from "../components/account-workspace";

export const metadata = {
  title: "Войти в личный кабинет — Лари",
};

export default function AccountPage() {
  return (
    <PageShell>
      <Section eyebrow="Личный кабинет" title="Войти в личный кабинет" className="bg-white">
        <InfoCallout title="Вход без пароля">
          Укажите email, чтобы получить ссылку для входа. Если вы уже сделали работу без email, она временно доступна в этом браузере 24 часа.
        </InfoCallout>
        <AccountWorkspace />
      </Section>
    </PageShell>
  );
}
