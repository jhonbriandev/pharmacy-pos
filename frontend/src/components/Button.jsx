import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
const VARIANTS = {
  primary:
    "bg-brand-700 text-white shadow-sm hover:bg-brand-800 active:bg-brand-900 disabled:bg-brand-700/50",
  secondary:
    "border border-slate-300 bg-white text-slate-800 shadow-sm hover:bg-slate-50 active:bg-slate-100",
  ghost: "text-slate-700 hover:bg-slate-100 active:bg-slate-200",
  danger:
    "bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800 disabled:bg-red-600/50",
};
const SIZES = {
  sm: "h-9 px-3 text-sm gap-1.5",
  md: "h-11 px-4 text-sm gap-2",
  lg: "h-12 px-5 text-base gap-2",
};
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  fullWidth = false,
  className,
  children,
  disabled,
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors",
        "disabled:cursor-not-allowed",
        VARIANTS[variant],
        SIZES[size],
        fullWidth && "w-full",
        className,
      )}
      {...props}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}
