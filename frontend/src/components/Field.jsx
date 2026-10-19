import { useId } from "react";
import { cn } from "@/lib/cn";
const CONTROL_BASE =
  "w-full rounded-lg border bg-white px-3 text-sm text-slate-900 shadow-sm transition-colors " +
  "placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 " +
  "disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";
/** Etiqueta + control + ayuda/error, con el espaciado ya resuelto. */
export function Field({ label, htmlFor, hint, error, required, children, className }) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-600">*</span>}
      </label>
      {children}
      {error ? (
        <p className="text-xs font-medium text-red-700">{error}</p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  );
}
export function Input({ className, invalid, ...props }) {
  return (
    <input
      aria-invalid={invalid || undefined}
      className={cn(
        CONTROL_BASE,
        "h-11",
        invalid ? "border-red-400" : "border-slate-300",
        className,
      )}
      {...props}
    />
  );
}
export function Select({ className, invalid, children, ...props }) {
  return (
    <select
      aria-invalid={invalid || undefined}
      className={cn(
        CONTROL_BASE,
        "h-11",
        invalid ? "border-red-400" : "border-slate-300",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
export function Textarea({ className, invalid, ...props }) {
  return (
    <textarea
      aria-invalid={invalid || undefined}
      className={cn(
        CONTROL_BASE,
        "min-h-20 py-2",
        invalid ? "border-red-400" : "border-slate-300",
        className,
      )}
      {...props}
    />
  );
}

/** Campo de texto con etiqueta, ya enlazado por id. */
export function TextField({ label, hint, error, required, className, invalid, ...props }) {
  const id = useId();
  return (
    <Field
      label={label}
      htmlFor={props.id ?? id}
      hint={hint}
      error={error}
      required={required}
      className={className}
    >
      <Input
        id={props.id ?? id}
        invalid={invalid ?? Boolean(error)}
        required={required}
        {...props}
      />
    </Field>
  );
}
