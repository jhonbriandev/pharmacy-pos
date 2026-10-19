# Convenciones de my-pos

Contexto para cualquier persona o agente que trabaje en este repositorio.
**Lee este archivo antes de escribir codigo.**

## Que es este proyecto

Punto de venta e inventario para una farmacia en Peru (una sucursal, un
almacen). Gestiona ventas, entradas y salidas de medicamentos con trazabilidad
por lote y vencimiento, autenticacion por roles y dashboard para gerencia.

## Stack

| Capa | Tecnologia | Notas |
|---|---|---|
| Backend | Django 5.2 LTS + DRF 3.18 | Se elige 5.2 LTS y **no** 6.x por compatibilidad declarada de las dependencias |
| Base de datos | PostgreSQL 18 | Nunca SQLite: invalidaria las pruebas de concurrencia |
| Frontend | React 19 + Vite 8 + JavaScript (JSX) | Sin TypeScript: el contrato con la API se documenta y se prueba, no se tipa |
| Estilos | Tailwind CSS 4 | |
| Estado de servidor | TanStack Query | Sin Redux |
| Pruebas backend | `TestCase` / `APITestCase` de Django + factory-boy | |
| Pruebas frontend | Vitest + Testing Library + MSW | |
| Formato frontend | Prettier | `npm run format` |

## Estructura

```
backend/
  config/            proyecto Django (settings, urls, wsgi/asgi)
    settings/        base.py | dev.py | prod.py   <- todo por variables de entorno
  apps/
    common/          base compartida: modelos abstractos, permisos, paginacion, excepciones
    accounts/        User personalizado (username = DNI), roles, autenticacion
    catalog/         laboratorios, categorias, principios activos, grupos, productos
    inventory/       lotes, libro mayor de movimientos, entradas, ajustes, FEFO
    sales/           ventas, lineas, asignacion de lotes, pagos
    reporting/       dashboard y exportaciones (solo lectura)
    audit/           registro inmutable de acciones sensibles
  tests/             pruebas transversales (permisos, concurrencia)
frontend/
  src/
    app/             router, providers, layout
    api/             cliente HTTP e interceptores
    features/        auth | pos | inventory | catalog | dashboard | users
    components/      UI reutilizable
    lib/             formato de moneda (S/) y fechas (dd/mm/yyyy)
docs/                documentacion del proyecto
scripts/             utilidades de entorno
```

## Reglas de arquitectura

1. **El backend es la autoridad.** El frontend presenta y solicita; no calcula
   precios, no decide stock, no elige lote y no decide permisos.
2. **El stock no se edita.** Todo cambio de stock pasa por
   `apps/inventory/services.py` y genera un `StockMovement` inmutable.
   Ningun serializer ni vista escribe cantidades directamente.
3. **La venta es una sola transaccion.** Venta, lineas, asignacion de lotes,
   movimientos y descuento de stock se confirman juntas o no se confirman.
4. **Cantidades enteras.** Cajas, blisteres y unidades son SKUs distintos
   dentro de un `ProductGroup`. El fraccionamiento (RF1-RF7, ver
   `apps/inventory/services.py`) convierte una presentacion mayor en la menor
   con dos movimientos en la misma transaccion, y el lote destino hereda el
   numero de lote y el vencimiento del origen.
5. **Dinero con `Decimal`**, nunca `float`. El IGV es el 18% y va incluido en
   el precio de venta; `Product.tax_rate` es informativo y la API no permite
   cambiarlo por producto.
6. **Fechas y vencimientos** se evaluan en `America/Lima`. Un lote vence al
   final de su fecha: es vendible ese dia y se bloquea desde el dia siguiente.
7. **Dependencias entre apps:** `common` y `accounts` no importan a nadie;
   `catalog` no importa a `inventory` ni a `sales`; `sales` puede importar
   `inventory`; `reporting` puede leer de todos y nadie lo importa.

## Reglas de trabajo

- Ningun secreto en el repositorio: solo `.env.example`. El `.env` real esta
  ignorado por git.
- Nunca usar datos reales de clientes o pacientes: los datos de `seed` son
  ficticios.
- No borrar migraciones, datos ni usuarios. Se desactiva (`is_active=False`),
  no se elimina.
- Toda funcionalidad nueva requiere pruebas de su comportamiento.
- Las pruebas del backend se escriben con `TestCase` (servicios y modelos) o
  `APITestCase` (API), con factories de `factory_boy`. La concurrencia usa
  `TransactionTestCase`.
- El backend se prueba **contra PostgreSQL**, no contra SQLite.

## Ramas y releases

- `main` es **produccion**: solo recibe merges de `develop` (o `release/*`) y se
  etiqueta con `vX.Y.Z` cuando se despliega.
- `develop` es la rama de integracion; la CI corre en cada push.
- El trabajo diario va en `feat/<tema>` o `fix/<tema>`, sale de `develop` y
  vuelve por pull request. No se hace push directo a `main`.
- Un arreglo urgente sale de `main` como `hotfix/<tema>`, se mergea a `main` y
  se vuelve a mergear a `develop` para no perderlo.

## Comandos

Dentro de `backend/` con el entorno virtual activado:

```powershell
python manage.py runserver
python manage.py migrate
python manage.py makemigrations
python manage.py seed
python manage.py test
ruff check .
```

Dentro de `frontend/`:

```powershell
npm run dev
npm run test
npm run build
npm run lint
npm run format
```
