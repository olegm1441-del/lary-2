import { PageShell, Section } from "../components/lary-ui";
import { AccountWorkspace } from "../components/account-workspace";

export const metadata = {
  title: "Войти в личный кабинет — Лари",
};

export default function AccountPage() {
  return (
    <PageShell>
      <Section eyebrow="Личный кабинет" title="Войти в личный кабинет" className="bg-white">
        <AccountWorkspace />
      </Section>
    </PageShell>
  );
}
