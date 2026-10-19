import { describe, expect, it } from "vitest";
import {
  addDaysIso,
  describeExpiry,
  formatDate,
  formatDateTime,
  formatInteger,
  formatMoney,
  parseDate,
  startOfMonthIso,
  todayIso,
} from "./format";
describe("formatMoney", () => {
  it("muestra soles con dos decimales", () => {
    expect(formatMoney("12.5")).toContain("12.50");
    expect(formatMoney("12.5")).toContain("S/");
  });
  it("no inventa decimales con binarios", () => {
    // 0.1 + 0.2 en float da 0.30000000000000004; con texto no hay sorpresa.
    expect(formatMoney("0.30")).toContain("0.30");
  });
  it("trata null y vacio como cero", () => {
    expect(formatMoney(null)).toContain("0.00");
    expect(formatMoney("")).toContain("0.00");
  });
});
describe("formatDate", () => {
  it("interpreta AAAA-MM-DD como fecha local, no UTC", () => {
    // En Lima, new Date("2027-01-27") mostraria el 26. Este es el error que
    // hacia que un lote apareciera vencido un dia antes.
    expect(formatDate("2027-01-27")).toBe("27/01/2027");
  });
  it("respeta la zona horaria America/Lima en fechas con hora", () => {
    expect(formatDateTime("2027-01-28T02:30:00Z")).toBe("27/01/2027 21:30");
  });
  it("devuelve un guion si no hay fecha", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("no-es-fecha")).toBe("—");
  });
});
describe("fechas de inventario", () => {
  it("suma dias cruzando fin de mes", () => {
    expect(addDaysIso("2027-01-31", 1)).toBe("2027-02-01");
  });
  it("describe el vencimiento en dias de calendario", () => {
    const today = todayIso();
    expect(describeExpiry(addDaysIso(today, 5))).toEqual({
      text: "vence en 5 dias",
      tone: "warning",
    });
    expect(describeExpiry(addDaysIso(today, 0))).toEqual({
      text: "vence hoy",
      tone: "warning",
    });
    expect(describeExpiry(addDaysIso(today, -1))).toEqual({
      text: "vencido ayer",
      tone: "danger",
    });
  });
  it("construye fechas sin desfase", () => {
    const parsed = parseDate("2026-03-01");
    expect(parsed?.getDate()).toBe(1);
    expect(parsed?.getMonth()).toBe(2);
  });
});
describe("otros formatos", () => {
  it("formatea enteros sin separador de miles en cantidades chicas", () => {
    expect(formatInteger(7)).toBe("7");
    expect(formatInteger(0)).toBe("0");
  });
  it("el primer dia del mes es el 01", () => {
    expect(startOfMonthIso().endsWith("-01")).toBe(true);
  });
});
