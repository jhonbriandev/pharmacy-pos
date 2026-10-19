import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { catalogApi } from "@/api/endpoints/catalog";
import { Input } from "@/components/Field";
import { Spinner } from "@/components/Feedback";
import { formatMoney } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";

/**
 * Buscador de productos para formularios.
 *
 * Deliberadamente simple: se escribe, se elige, se limpia. Un combo
 * precargado con cientos de productos obliga a scrollear y a cargar de mas.
 */
export function ProductPicker({
  onSelect,
  placeholder = "Buscar producto por nombre o codigo…",
  excludeIds = [],
}) {
  const [term, setTerm] = useState("");
  const debounced = useDebouncedValue(term.trim(), 250);
  const inputRef = useRef(null);
  const resultsQuery = useQuery({
    queryKey: ["lookup", "picker", debounced],
    queryFn: () => catalogApi.search(debounced),
    enabled: debounced.length >= 2,
    staleTime: 10_000,
  });
  const results = (resultsQuery.data ?? []).filter((product) => !excludeIds.includes(product.id));
  return (
    <div className="space-y-2">
      <div className="relative">
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
          aria-hidden
        />
        <Input
          ref={inputRef}
          placeholder={placeholder}
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          className="pl-9"
        />
      </div>

      {debounced.length >= 2 && (
        <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-200">
          {resultsQuery.isFetching ? (
            <Spinner label="Buscando" />
          ) : results.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {results.map((product) => (
                <li key={product.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-slate-50"
                    onClick={() => {
                      onSelect(product);
                      setTerm("");
                      inputRef.current?.focus();
                    }}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-slate-900">
                        {product.display_name}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {product.barcode ?? "sin codigo"} · stock {product.stock}
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums">{formatMoney(product.sale_price)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-3 py-4 text-center text-sm text-slate-500">Sin coincidencias.</p>
          )}
        </div>
      )}
    </div>
  );
}
