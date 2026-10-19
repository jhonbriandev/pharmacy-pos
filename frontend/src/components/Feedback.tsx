import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";

type Tone = "info" | "success" | "warning" | "danger";

const TONES: Record<Tone, { wrapper: string; icon: ReactNode }> = {
  info: {
    wrapper: "border-sky-200 bg-sky-50 text-sky-900",
    icon: <Info className="size-4 shrink-0" aria-hidden />,
  },
  success: {
    wrapper: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: <CheckCircle2 className="size-4 shrink-0" aria-hidden />,
  },
  warning: {
    wrapper: "border-amber-200 bg-amber-50 text-amber-900",
    icon: <AlertTriangle className="size-4 shrink-0" aria-hidden />,
  },
  danger: {
    wrapper: "border-red-200 bg-red-50 text-red-900",
    icon: <XCircle className="size-4 shrink-0" aria-hidden />,
  },
};

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  const config = TONES[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("flex gap-2 rounded-lg border p-3 text-sm", config.wrapper, className)}
    >
      {config.icon}
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "mt-0.5" : undefined}>{children}</div>}
      </div>
    </div>
  );
}

export function Spinner({ label = "Cargando" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      <span>{label}…</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      {description && <p className="max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <p className="font-semibold">No se pudo cargar la informacion</p>
      <p className="mt-1">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-50"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
