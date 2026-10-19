/** Une clases condicionales sin dependencias externas. */
export function cn(...values) {
  return values.filter(Boolean).join(" ");
}
