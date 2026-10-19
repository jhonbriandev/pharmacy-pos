import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, Menu, Plus, Settings, X } from "lucide-react";

import { Button } from "@/components/Button";
import { cn } from "@/lib/cn";
import { useAuth } from "@/features/auth/context";
import { NAV_ITEMS } from "./navigation";

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("");
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex size-9 items-center justify-center rounded-lg bg-brand-700 text-white">
        <Plus className="size-5" aria-hidden />
      </span>
      <span>
        <span className="block text-sm font-semibold tracking-[0.14em] text-slate-900 uppercase">
          my-pos
        </span>
        <span className="block text-xs text-slate-500">Farmacia</span>
      </span>
    </Link>
  );
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <nav className="flex flex-1 flex-col gap-1" aria-label="Navegacion principal">
      {NAV_ITEMS.filter((item) => item.visible(user.capabilities)).map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-brand-50 text-brand-800"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <item.icon className="size-4.5 shrink-0" aria-hidden />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

function UserCard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [leaving, setLeaving] = useState(false);

  if (!user) return null;

  async function handleLogout() {
    setLeaving(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setLeaving(false);
    }
  }

  return (
    <div className="border-t border-slate-200 pt-3">
      <div className="flex items-center gap-3 px-1">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-200 text-sm font-semibold text-slate-700">
          {initials(user.full_name)}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900">{user.full_name}</p>
          <p className="truncate text-xs text-slate-500">{user.role_display}</p>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-1">
        <Link
          to="/cambiar-clave"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          <Settings className="size-4" aria-hidden />
          Cambiar contrasena
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          disabled={leaving}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-60"
        >
          <LogOut className="size-4" aria-hidden />
          {leaving ? "Cerrando…" : "Cerrar sesion"}
        </button>
      </div>
    </div>
  );
}

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[16.5rem_1fr]">
      {/* Barra lateral fija en escritorio. */}
      <aside className="hidden flex-col gap-6 border-r border-slate-200 bg-white px-4 py-5 lg:sticky lg:top-0 lg:flex lg:h-screen">
        <Brand />
        <Navigation />
        <UserCard />
      </aside>

      {/* Menu emergente en pantallas pequenas. */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar menu"
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMenuOpen(false)}
          />
          <div className="relative flex h-full w-72 flex-col gap-6 bg-white px-4 py-5 shadow-xl">
            <div className="flex items-center justify-between">
              <Brand />
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-100"
                aria-label="Cerrar menu"
              >
                <X className="size-5" aria-hidden />
              </button>
            </div>
            <Navigation onNavigate={() => setMenuOpen(false)} />
            <UserCard />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setMenuOpen(true)}
              aria-label="Abrir menu"
              icon={<Menu className="size-5" aria-hidden />}
            />
            <Brand />
          </div>
          <span className="truncate text-sm text-slate-600">{user?.first_name}</span>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
