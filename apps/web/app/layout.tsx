import type { Metadata } from "next";
import "./globals.css";
import { buildSha } from "./lib/build-info";

export const metadata: Metadata = {
  title: "Лари — AI-помощник по составлению грантовых заявок",
  description: "Соберите документы, письма, расчеты, презентации и сценарные планы для грантовой заявки.",
  other: {
    "lari-build-sha": buildSha,
  },
};

export const dynamic = "force-dynamic";
export const revalidate = 0;

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
