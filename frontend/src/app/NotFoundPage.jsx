import { useNavigate } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "@/components/Button";
export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <Compass className="size-10 text-slate-300" aria-hidden />
      <h1 className="text-2xl font-semibold text-slate-900">Pagina no encontrada</h1>
      <p className="max-w-sm text-sm text-slate-500">
        La direccion que abriste no existe o cambio de lugar.
      </p>
      <Button className="mt-2" onClick={() => navigate("/")}>
        Volver al inicio
      </Button>
    </div>
  );
}
