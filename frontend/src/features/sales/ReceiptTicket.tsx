import type { Receipt } from "@/api/types";
import { formatDate, formatMoney, formatTime } from "@/lib/format";

/**
 * Boleta para el cliente.
 *
 * Se imprime en papel de 80 mm. Deliberadamente **no** muestra costo ni
 * margen, y recuerda que no es un comprobante fiscal: en Peru la boleta de
 * venta con validez tributaria la emite el sistema de facturacion electronica,
 * que no forma parte de este MVP.
 */
export function ReceiptTicket({ receipt }: { receipt: Receipt }) {
  return (
    <div className="print-area mx-auto w-full max-w-sm border border-slate-200 bg-white p-5 font-mono text-xs leading-relaxed text-slate-900">
      <div className="text-center">
        <p className="text-sm font-bold tracking-wide uppercase">my-pos · Farmacia</p>
        <p className="mt-1">Boleta de venta interna</p>
        <p className="text-[10px] text-slate-500">No es comprobante fiscal</p>
      </div>

      <div className="my-3 space-y-0.5 border-y border-dashed border-slate-400 py-2">
        <p className="flex justify-between">
          <span>N°</span>
          <span className="font-bold">{receipt.number}</span>
        </p>
        <p className="flex justify-between">
          <span>Fecha</span>
          <span>{formatDate(receipt.created_at)}</span>
        </p>
        <p className="flex justify-between">
          <span>Hora</span>
          <span>{formatTime(receipt.created_at)}</span>
        </p>
        <p className="flex justify-between">
          <span>Atendio</span>
          <span>{receipt.seller_name || "—"}</span>
        </p>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b border-dashed border-slate-400 text-left">
            <th className="pb-1 font-semibold">Descripcion</th>
            <th className="pb-1 text-center font-semibold">Cant</th>
            <th className="pb-1 text-right font-semibold">Importe</th>
          </tr>
        </thead>
        <tbody>
          {receipt.items.map((item, index) => (
            <tr key={`${item.product_name}-${index}`} className="align-top">
              <td className="py-1 pr-2">
                {item.product_name}
                <span className="block text-[10px] text-slate-500">
                  {formatMoney(item.unit_price)} c/u
                </span>
              </td>
              <td className="py-1 text-center tabular-nums">{item.quantity}</td>
              <td className="py-1 text-right tabular-nums">{formatMoney(item.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-3 border-t border-dashed border-slate-400 pt-2">
        <p className="flex justify-between text-sm font-bold">
          <span>TOTAL</span>
          <span className="tabular-nums">{formatMoney(receipt.total)}</span>
        </p>
        <p className="mt-1 flex justify-between">
          <span>Pago</span>
          <span>{receipt.payment?.method ?? "—"}</span>
        </p>
        {receipt.payment?.received_amount && (
          <p className="flex justify-between">
            <span>Recibido</span>
            <span className="tabular-nums">{formatMoney(receipt.payment.received_amount)}</span>
          </p>
        )}
        {receipt.payment && Number(receipt.payment.change_amount) > 0 && (
          <p className="flex justify-between font-semibold">
            <span>Vuelto</span>
            <span className="tabular-nums">{formatMoney(receipt.payment.change_amount)}</span>
          </p>
        )}
        {receipt.payment?.reference && (
          <p className="flex justify-between">
            <span>Referencia</span>
            <span>{receipt.payment.reference}</span>
          </p>
        )}
      </div>

      <p className="mt-4 text-center text-[10px] text-slate-500">
        Gracias por su compra. Conserve este documento.
      </p>
    </div>
  );
}
