import { describe, expect, it } from "vitest";

import { cartQuantity, cartTotalCents, fromCents, toCents, toSaleItems, type CartLine } from "./cart";

function line(unitPrice: string, quantity: number): CartLine {
  return {
    productId: 1,
    name: "Paracetamol",
    unitPrice,
    quantity,
    availableStock: 10,
    presentation: "Caja",
    unitLabel: "caja",
  };
}

describe("aritmetica del carrito", () => {
  it("suma en centavos, sin errores de coma flotante", () => {
    // 0.10 + 0.20 en float es 0.30000000000000004; en centavos es 30.
    const total = cartTotalCents([line("0.10", 1), line("0.20", 1)]);
    expect(total).toBe(30);
    expect(fromCents(total)).toBe("0.30");
  });

  it("multiplica precio por cantidad", () => {
    expect(cartTotalCents([line("12.50", 3)])).toBe(3750);
  });

  it("convierte montos con mas de dos decimales al centavo mas cercano", () => {
    expect(toCents("8.005")).toBe(801);
    expect(toCents("8.004")).toBe(800);
  });

  it("cuenta unidades, no lineas", () => {
    expect(cartQuantity([line("1.00", 2), line("2.00", 5)])).toBe(7);
  });

  it("envia al backend solo producto y cantidad", () => {
    expect(toSaleItems([line("1.00", 2)])).toEqual([{ product_id: 1, quantity: 2 }]);
  });
});
