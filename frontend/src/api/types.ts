/**
 * Tipos de la API.
 *
 * Se escriben a mano (no se generan) porque la API es pequena y estable: un
 * archivo legible vale mas que un generador que nadie revisa.
 *
 * **El dinero llega como texto**, igual que en el backend. Convertirlo a
 * `number` solo al formatear evita errores de redondeo en los totales.
 */

export type Role = "ADMIN" | "REGENTE" | "CAJERO" | "ALMACEN" | "AUDITOR";

export type Presentation =
  | "CAJA"
  | "BLISTER"
  | "UNIDAD"
  | "FRASCO"
  | "TUBO"
  | "AMPOLLA"
  | "SOBRE"
  | "OTRO";

export type PharmaceuticalForm =
  | "TABLETA"
  | "CAPSULA"
  | "JARABE"
  | "SUSPENSION"
  | "SOLUCION"
  | "CREMA"
  | "GEL"
  | "GOTAS"
  | "INYECTABLE"
  | "SUPOSITORIO"
  | "POLVO"
  | "UNGUENTO";

export type MovementType =
  | "ENTRADA"
  | "SALIDA_VENTA"
  | "AJUSTE_POSITIVO"
  | "AJUSTE_NEGATIVO"
  | "BAJA_VENCIMIENTO"
  | "BAJA_AVERIA"
  | "FRACCIONAMIENTO_SALIDA"
  | "FRACCIONAMIENTO_ENTRADA";

export type PaymentMethod = "EFECTIVO" | "TARJETA" | "TRANSFERENCIA";

export type SaleStatus = "CONFIRMADA" | "ANULADA";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Capabilities {
  can_sell: boolean;
  can_manage_inventory: boolean;
  can_manage_catalog: boolean;
  can_manage_users: boolean;
  can_view_dashboard: boolean;
  can_view_all_sales: boolean;
  can_read_audit: boolean;
}

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  role: Role;
  role_display: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login: string | null;
}

export interface Me extends User {
  capabilities: Capabilities;
}

export interface RoleOption {
  value: Role;
  label: string;
}

export interface Laboratory {
  id: number;
  name: string;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
}

export interface ActiveIngredient {
  id: number;
  name: string;
  is_active: boolean;
}

export interface ProductGroup {
  id: number;
  name: string;
  concentration: string;
  pharmaceutical_form: PharmaceuticalForm;
  laboratory: number | null;
  laboratory_name: string;
  category: number | null;
  category_name: string;
  ingredients: ActiveIngredient[];
  notes: string;
  is_active: boolean;
  display_name: string;
}

export interface Product {
  id: number;
  group: number;
  group_name: string;
  display_name: string;
  presentation: Presentation;
  presentation_display: string;
  presentation_detail: string;
  barcode: string | null;
  unit_label: string;
  sale_price: string;
  tax_rate: string;
  last_cost: string;
  margin: string;
  min_stock: number;
  is_active: boolean;
  stock: number;
}

export interface LookupLot {
  id: number;
  batch_number: string;
  expiry_date: string;
  quantity: number;
}

export interface ProductLookup {
  id: number;
  display_name: string;
  barcode: string | null;
  presentation: Presentation;
  presentation_display: string;
  sale_price: string;
  tax_rate: string;
  last_cost: string;
  stock: number;
  lots: LookupLot[];
}

export interface Lot {
  id: number;
  product: number;
  product_name: string;
  batch_number: string;
  expiry_date: string;
  current_quantity: number;
  cost_price: string;
  is_blocked: boolean;
  block_reason: string;
  is_expired: boolean;
  available: boolean;
}

export interface UnitConversion {
  id: number;
  group: number;
  source: number;
  source_label: string;
  target: number;
  target_label: string;
  factor: number;
}

export interface StockMovement {
  id: number;
  created_at: string;
  movement_type: MovementType;
  movement_type_display: string;
  product: number;
  product_name: string;
  lot: number;
  lot_batch: string;
  quantity_delta: number;
  balance_after: number;
  reason: string;
  notes: string;
  reference_type: string;
  reference_id: number | null;
  created_by: number | null;
  created_by_name: string;
}

export interface StockEntryItem {
  id: number;
  product: number;
  product_name: string;
  batch_number: string;
  expiry_date: string;
  quantity: number;
  cost_price: string;
}

export interface StockEntry {
  id: number;
  received_at: string;
  supplier: string;
  document_number: string;
  notes: string;
  items: StockEntryItem[];
  created_by: number | null;
  created_by_name: string;
  created_at: string;
}

export interface SaleItemLot {
  id: number;
  lot: number;
  batch_number: string;
  expiry_date: string;
  quantity: number;
  unit_cost: string;
}

export interface SaleItem {
  id: number;
  product: number;
  product_name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  unit_cost: string;
  margin: string;
  lot_allocations: SaleItemLot[];
}

export interface Payment {
  id: number;
  method: PaymentMethod;
  method_display: string;
  amount: string;
  received_amount: string | null;
  change_amount: string;
  reference: string;
}

export interface Sale {
  id: number;
  number: string;
  status: SaleStatus;
  status_display: string;
  total: string;
  items: SaleItem[];
  payments: Payment[];
  created_by: number | null;
  seller_name: string;
  created_at: string;
  notes: string;
}

export interface ReceiptItem {
  product_name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface ReceiptPayment {
  method: string;
  amount: string;
  received_amount: string | null;
  change_amount: string;
  reference: string;
}

export interface Receipt {
  number: string;
  created_at: string;
  seller_name: string;
  items: ReceiptItem[];
  total: string;
  payment: ReceiptPayment | null;
}

export interface DashboardSummary {
  date_from: string;
  date_to: string;
  sales_total: string;
  sales_count: number;
  average_ticket: string;
}

export interface DashboardDay {
  date: string;
  total: string;
  count: number;
}

export interface PaymentBreakdown {
  method: PaymentMethod;
  label: string;
  total: string;
  count: number;
}

export interface TopProduct {
  product_id: number;
  product_name: string;
  quantity: number;
  total: string;
}

export interface GrossMargin {
  revenue: string;
  cost: string;
  margin: string;
  margin_percentage: string;
}

export interface LowStockAlert {
  product_id: number;
  product_name: string;
  stock: number;
  min_stock: number;
}

export interface ExpiringLot {
  lot_id: number;
  product_name: string;
  batch_number: string;
  expiry_date: string;
  days_left: number;
  quantity: number;
}

export interface ExpiredLot {
  lot_id: number;
  product_name: string;
  batch_number: string;
  expiry_date: string;
  days_overdue: number;
  quantity: number;
}

export interface InventoryValue {
  units: number;
  cost_value: string;
}

export interface Dashboard {
  period: { date_from: string; date_to: string };
  summary: DashboardSummary;
  sales_by_day: DashboardDay[];
  sales_by_payment_method: PaymentBreakdown[];
  top_products: TopProduct[];
  gross_margin: GrossMargin;
  low_stock: LowStockAlert[];
  expiring_lots: ExpiringLot[];
  expired_lots: ExpiredLot[];
  inventory: InventoryValue;
  generated_at: string;
}

export interface AuditEvent {
  id: number;
  created_at: string;
  action: string;
  action_display: string;
  actor: number | null;
  actor_name: string;
  actor_username: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip_address: string | null;
}

export interface ConsistencyReport {
  consistent: boolean;
  issues_count: number;
  issues: Array<{
    lot_id: number;
    product: string;
    batch_number: string;
    cached: number;
    ledger: number;
    difference: number;
  }>;
}
