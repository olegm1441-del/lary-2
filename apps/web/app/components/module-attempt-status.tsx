"use client";

import { useEffect, useState } from "react";
import { isModuleAttemptUsed, MODULE_ATTEMPT_USED_EVENT } from "../lib/module-attempts";

export function ModuleAttemptStatus({ moduleSlug, className = "" }: { moduleSlug: string; className?: string }) {
  const [used, setUsed] = useState(false);

  useEffect(() => {
    const update = () => setUsed(isModuleAttemptUsed(moduleSlug));
    update();
    window.addEventListener("storage", update);
    window.addEventListener(MODULE_ATTEMPT_USED_EVENT, update);
    return () => {
      window.removeEventListener("storage", update);
      window.removeEventListener(MODULE_ATTEMPT_USED_EVENT, update);
    };
  }, [moduleSlug]);

  return (
    <p className={`${className || "mt-5"} rounded-2xl p-4 text-base font-semibold ${used ? "bg-red-50 text-red-800" : "bg-green-50 text-green-800"}`}>
      {used ? "необходимо купить запуск модуля" : "1 бесплатный запуск в этом модуле"}
    </p>
  );
}
