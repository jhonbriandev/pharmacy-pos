import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({
  title,
  description,
  actions,
  children,
  className,
  padded = true,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section
      className={cn(
        "rounded-[var(--radius-card)] border border-slate-200 bg-white shadow-sm",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={padded ? "p-5" : undefined}>{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "positive" | "warning" | "danger";
}) {
  const tones = {
    default: "text-slate-900",
    positive: "text-brand-700",
    warning: "text-amber-700",
    danger: "text-red-700",
  } as const;

  return (
    <div className="rounded-[var(--radius-card)] border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
      <p className={cn("mt-2 text-2xl font-semibold tabular-nums", tones[tone])}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
