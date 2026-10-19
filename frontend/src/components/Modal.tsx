import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { cn } from "@/lib/cn";

const SIZES = {
  sm: "max-w-md",
  md: "max-w-2xl",
  lg: "max-w-4xl",
  xl: "max-w-6xl",
} as const;

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: keyof typeof SIZES;
  /** Desactiva el cierre al hacer clic fuera (para operaciones en curso). */
  dismissible?: boolean;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  dismissible = true,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && dismissible) {
        event.stopPropagation();
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // El foco entra al primer campo util, no al boton de cerrar.
    const firstField = panelRef.current?.querySelector<HTMLElement>(
      "input:not([type='hidden']), select, textarea",
    );
    (firstField ?? panelRef.current)?.focus();

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose, dismissible]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:items-center">
      <button
        type="button"
        aria-label="Cerrar"
        tabIndex={-1}
        className="absolute inset-0 cursor-default"
        onClick={dismissible ? onClose : undefined}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn(
          "relative my-8 w-full rounded-[var(--radius-card)] bg-white shadow-xl outline-none",
          SIZES[size],
        )}
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={!dismissible}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-40"
            aria-label="Cerrar"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>

        <div className="px-5 py-4">{children}</div>

        {footer && (
          <footer className="flex flex-wrap justify-end gap-2 border-t border-slate-200 bg-slate-50/70 px-5 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}
