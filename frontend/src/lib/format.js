/**
 * Formato de dinero y fechas para Peru.
 *
 * Dos trampas que este archivo resuelve de una vez:
 *
 * 1. **El dinero llega como texto.** Convertirlo a `number` para sumar es
 *    incorrecto; aqui solo se convierte para *mostrar*. Los totales siempre
 *    vienen calculados del servidor.
 * 2. **`new Date("2027-01-27")` interpreta UTC.** En Lima (UTC-5) eso muestra
 *    el 26 de enero: un dia antes del vencimiento real. Las fechas sin hora se
 *    construyen como fecha local, a mano.
 */

const PEN = new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const DECIMAL_2 = new Intl.NumberFormat("es-PE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const INTEGER = new Intl.NumberFormat("es-PE", {
  maximumFractionDigits: 0,
});
function toNumber(value) {
  if (value === null || value === undefined || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** S/ 12.50 */
export function formatMoney(value) {
  return PEN.format(toNumber(value));
}

/** 12.50 (sin simbolo, para tablas donde la columna ya dice "Precio") */
export function formatAmount(value) {
  return DECIMAL_2.format(toNumber(value));
}
export function formatInteger(value) {
  return INTEGER.format(value ?? 0);
}
export function formatPercent(value) {
  return `${DECIMAL_2.format(toNumber(value))} %`;
}

/** Convierte "2027-01-27" o "2027-01-27T10:00:00-05:00" en Date local. */
export function parseDate(value) {
  if (!value) return null;
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Date(Number(year), Number(month) - 1, Number(day));
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
function pad(value) {
  return value.toString().padStart(2, "0");
}

/** 27/01/2027 */
export function formatDate(value) {
  const date = parseDate(value);
  if (!date) return "—";
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}

/** 27/01/2027 14:05 */
export function formatDateTime(value) {
  const date = parseDate(value);
  if (!date) return "—";
  return `${formatDate(value)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 14:05 */
export function formatTime(value) {
  const date = parseDate(value);
  if (!date) return "—";
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Fecha de hoy en formato AAAA-MM-DD, en hora local del equipo. */
export function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Primer dia del mes en curso, en formato AAAA-MM-DD. */
export function startOfMonthIso() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-01`;
}

/** Suma dias a una fecha AAAA-MM-DD sin cruzar zonas horarias. */
export function addDaysIso(value, days) {
  const date = parseDate(value);
  if (!date) return value;
  date.setDate(date.getDate() + days);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** "vence en 12 dias" / "vencido hace 3 dias" / "vence hoy". */
export function describeExpiry(expiryDate) {
  const expiry = parseDate(expiryDate);
  if (!expiry)
    return {
      text: "—",
      tone: "neutral",
    };
  const today = parseDate(todayIso());
  const days = Math.round((expiry.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) {
    const overdue = Math.abs(days);
    return {
      text: overdue === 1 ? "vencido ayer" : `vencido hace ${overdue} dias`,
      tone: "danger",
    };
  }
  if (days === 0)
    return {
      text: "vence hoy",
      tone: "warning",
    };
  if (days <= 30)
    return {
      text: `vence en ${days} dias`,
      tone: "warning",
    };
  return {
    text: `vence en ${days} dias`,
    tone: "neutral",
  };
}

/** Normaliza un monto tecleado por el usuario a texto con dos decimales. */
export function normalizeMoneyInput(value) {
  const cleaned = value.replace(/[^\d.]/g, "").replace(/(\..*)\./g, "$1");
  if (cleaned === "") return "";
  return cleaned;
}

/** Convierte "12.5" en "12.50"; util para enviar al backend. */
export function toMoneyString(value) {
  return toNumber(value).toFixed(2);
}
