"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

type Toast = { id: number; kind: "success" | "error" | "info"; message: string };
const ToastContext = createContext<{ toast: (kind: Toast["kind"], message: string) => void } | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toast = useCallback((kind: Toast["kind"], message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id}
            className={`flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm shadow-pop bg-white ${
              t.kind === "error" ? "border-red-200 text-red-800"
              : t.kind === "success" ? "border-emerald-200 text-emerald-800"
              : "border-slate-200 text-slate-700"}`}>
            {t.kind === "error" ? <XCircle size={16} className="mt-0.5 shrink-0" />
              : t.kind === "success" ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
              : <AlertTriangle size={16} className="mt-0.5 shrink-0" />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  return ctx ?? { toast: () => {} };
}
