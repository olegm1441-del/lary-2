import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Лари — модульный помощник для заявки ПФКИ",
  description: "Соберите документы, письма, расчеты, презентации и сценарные планы для заявки ПФКИ.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="h-full scroll-smooth antialiased" data-scroll-behavior="smooth">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
