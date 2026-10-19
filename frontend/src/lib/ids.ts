/**
 * Identificador de peticion idempotente.
 *
 * El backend guarda este valor en ventas y entradas de mercaderia: si la red
 * falla y el usuario reintenta, devuelve la operacion ya creada en lugar de
 * duplicarla. Debe generarse una vez por intento logico, no por clic.
 */
export function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  // Navegadores antiguos o contextos sin crypto: se arma un UUID v4 a mano.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0;
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}
