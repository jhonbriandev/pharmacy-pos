/**
 * Aritmetica de mostrador.
 *
 * El servidor es la autoridad: el total que se cobra y el que queda guardado
 * los calcula Django. Estas funciones existen solo para mostrar un subtotal
 * mientras se arma el carrito, y trabajan en **centavos enteros** para que
 * sumar 0.10 + 0.20 nunca produzca 0.30000000000000004.
 */

export function toCents(amount) {
  const value = typeof amount === "number" ? amount : Number(amount);
  if (!Number.isFinite(value)) return 0;
  return Math.round(value * 100);
}
export function fromCents(cents) {
  return (cents / 100).toFixed(2);
}
export function formatCents(cents) {
  return new Intl.NumberFormat("es-PE", {
    style: "currency",
    currency: "PEN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}
export function cartTotalCents(lines) {
  return lines.reduce((total, line) => total + toCents(line.unitPrice) * line.quantity, 0);
}
export function cartQuantity(lines) {
  return lines.reduce((total, line) => total + line.quantity, 0);
}
export function toSaleItems(lines) {
  return lines.map((line) => ({
    product_id: line.productId,
    quantity: line.quantity,
  }));
}
