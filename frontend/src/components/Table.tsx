import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/cn";
import { Button } from "./Button";

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full min-w-full border-collapse text-sm", className)}>{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">
      {children}
    </thead>
  );
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-slate-100">{children}</tbody>;
}

export function TR({
  children,
  className,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(onClick && "cursor-pointer hover:bg-slate-50", className)}
    >
      {children}
    </tr>
  );
}

export function TH({ children, className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th className={cn("px-4 py-2.5 font-semibold whitespace-nowrap", className)} {...props}>
      {children}
    </th>
  );
}

export function TD({ children, className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("px-4 py-2.5 align-middle text-slate-700", className)} {...props}>
      {children}
    </td>
  );
}

/** Mensaje a lo ancho de la tabla (vacio, cargando o error). */
export function TableMessage({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-10 text-center text-sm text-slate-500">
        {children}
      </td>
    </tr>
  );
}

export function Pagination({
  page,
  pageSize,
  count,
  onChange,
}: {
  page: number;
  pageSize: number;
  count: number;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span className="tabular-nums">
        {from}–{to} de {count}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          icon={<ChevronLeft className="size-4" aria-hidden />}
        >
          Anterior
        </Button>
        <span className="tabular-nums text-slate-500">
          {page} / {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
        >
          Siguiente
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
