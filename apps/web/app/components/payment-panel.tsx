"use client";

import { useState } from "react";
import { apiUrl, readApiError } from "../lib/api-client";

type PaymentPackage = "single" | "six";

export function PaymentPanel() {
  const [promoCode, setPromoCode] = useState("");
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"idle" | "submitting" | "success" | "error">("idle");

  async function buyPackage(paymentPackage: PaymentPackage) {
    setState("submitting");
    setMessage("Создаем платеж. Заполненная форма модуля сохранится.");
    try {
      const response = await fetch(apiUrl("/api/payments/create"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ package: paymentPackage }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setState("success");
      setMessage(`Платеж создан. Запусков: ${payload.runs}. Сумма: ${payload.amount_rub} ₽. После подключения провайдера здесь будет переход к оплате.`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Оплата не завершена. Запуск не списан. Попробуйте снова или выберите другой способ.");
    }
  }

  async function applyPromo() {
    setState("submitting");
    setMessage("Проверяем промокод...");
    try {
      const response = await fetch(apiUrl("/api/promos/apply"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: promoCode }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const payload = await response.json();
      setState("success");
      setMessage(payload.message || `Промокод применен. Добавлено запусков: ${payload.added_runs}.`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Такой промокод не найден. Проверьте буквы и цифры.");
    }
  }

  return (
    <div className="mt-10 grid gap-5 lg:grid-cols-3">
      <div className="rounded-3xl border border-slate-200 p-6">
        <p className="text-3xl font-bold">1 запуск</p>
        <p className="mt-4 text-lg leading-8 text-slate-700">320 ₽. Для повторного запуска одного модуля или быстрой проверки идеи.</p>
        <button type="button" onClick={() => void buyPackage("single")} className="mt-6 min-h-14 w-full rounded-2xl bg-blue-800 px-5 py-4 text-lg font-semibold text-white">
          Купить 1 запуск
        </button>
      </div>
      <div className="rounded-3xl border-2 border-blue-800 p-6">
        <p className="text-3xl font-bold">6 запусков</p>
        <p className="mt-4 text-lg leading-8 text-slate-700">1920 ₽. Пакет под все шесть MVP-модулей или несколько попыток в нужном модуле.</p>
        <button type="button" onClick={() => void buyPackage("six")} className="mt-6 min-h-14 w-full rounded-2xl bg-blue-800 px-5 py-4 text-lg font-semibold text-white">
          Купить пакет
        </button>
      </div>
      <div className="rounded-3xl border border-slate-200 p-6">
        <p className="text-3xl font-bold">Промокод</p>
        <p className="mt-4 text-lg leading-8 text-slate-700">Введите код, если он у вас есть.</p>
        <label className="mt-6 grid gap-2">
          <span className="text-base font-semibold text-slate-800">Промокод</span>
          <input
            type="text"
            value={promoCode}
            onChange={(event) => setPromoCode(event.target.value)}
            placeholder="Например: LARY-START"
            className="min-h-14 rounded-2xl border border-slate-300 bg-slate-50 px-4 text-lg outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <button type="button" onClick={() => void applyPromo()} className="mt-4 min-h-14 w-full rounded-2xl border border-blue-800 px-5 py-4 text-lg font-semibold text-blue-800 hover:bg-blue-50">
          Применить
        </button>
      </div>
      {message ? (
        <p className={`lg:col-span-3 rounded-2xl p-4 text-lg leading-8 ${state === "error" ? "bg-red-50 text-red-900" : "bg-green-50 text-green-900"}`}>
          {message}
        </p>
      ) : null}
    </div>
  );
}
