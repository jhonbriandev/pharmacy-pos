import type { Capabilities } from "@/api/types";
import {
  Boxes,
  LayoutDashboard,
  Package,
  Pill,
  ScrollText,
  ShoppingCart,
  Users,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: typeof ShoppingCart;
  visible: (capabilities: Capabilities) => boolean;
}

const everyone = () => true;

/** Menu principal. Lo que no corresponde al rol no se muestra ni se resuelve. */
export const NAV_ITEMS: NavItem[] = [
  {
    to: "/pos",
    label: "Punto de venta",
    icon: ShoppingCart,
    visible: (capabilities) => capabilities.can_sell,
  },
  {
    to: "/ventas",
    label: "Ventas",
    icon: ScrollText,
    visible: everyone,
  },
  {
    to: "/inventario",
    label: "Inventario",
    icon: Boxes,
    visible: (capabilities) => capabilities.can_manage_inventory || capabilities.can_read_audit,
  },
  {
    to: "/catalogo",
    label: "Catalogo",
    icon: Pill,
    visible: everyone,
  },
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    visible: (capabilities) => capabilities.can_view_dashboard,
  },
  {
    to: "/usuarios",
    label: "Usuarios",
    icon: Users,
    visible: (capabilities) => capabilities.can_manage_users,
  },
  {
    to: "/auditoria",
    label: "Auditoria",
    icon: Package,
    visible: (capabilities) => capabilities.can_read_audit,
  },
];

/** Ruta de inicio segun el rol: quien no vende no deberia aterrizar en el POS. */
export function homePathFor(capabilities: Capabilities): string {
  if (capabilities.can_sell) return "/pos";
  if (capabilities.can_view_dashboard) return "/dashboard";
  return "/inventario";
}
