# Arquitectura

## Vision general

my-pos es una aplicacion de dos capas con una regla central: **el backend es la
autoridad**. El frontend presenta datos y solicita operaciones; nunca decide un
precio, un lote, un descuento de stock ni un permiso.

```
+---------------------------+        HTTPS         +---------------------------+
|  React 19 + Vite + TS     |  fetch + cookies   |  Django 5.2 + DRF         |
|  Tailwind 4               | <----------------> |  sesion + CSRF            |
|  TanStack Query           |                    |                           |
+---------------------------+                    +-------------+-------------+
                                                               |
                                                   +-----------v-----------+
                                                   |  PostgreSQL 18        |
                                                   |  ledger + agregados   |
                                                   +-----------------------+
```

En produccion el navegador ve **un solo origen**: Vercel sirve el frontend y
reenvia `/api/*` al backend de Render (ver `docs/operacion.md`). Eso evita CORS
y permite cookies `SameSite=Lax`.

## Capas del backend

| App | Responsabilidad | Puede importar |
|---|---|---|
| `common` | modelos abstractos, permisos base, paginacion, excepciones | nada del proyecto |
| `accounts` | usuario (DNI), roles, login/logout, gestion de cuentas | `common` |
| `catalog` | laboratorios, categorias, principios activos, grupos, productos y conversiones | `common`, `accounts` |
| `inventory` | lotes, libro de movimientos, entradas, ajustes, FEFO, fraccionamiento | `catalog` |
| `sales` | ventas, lineas, asignacion de lotes, pagos, numeracion, boleta | `inventory`, `catalog` |
| `reporting` | dashboard y exportaciones CSV (solo lectura) | todos |
| `audit` | registro inmutable de acciones sensibles | `accounts` |

Reglas:

- `common` y `accounts` no importan a nadie.
- `catalog` no importa a `inventory` ni a `sales`.
- `sales` si importa `inventory`: vender es mover stock.
- `reporting` lee de todos y nadie lo importa.

**Desvio deliberado documentado:** `catalog` importa funciones de
`inventory.services` en tres vistas de consulta (`lookup`, `low-stock`,
`{id}/lots`) para devolver stock vendible en una sola respuesta. La alternativa
era duplicar la logica de FEFO en el catalogo, que es peor. Ver
`docs/decisiones.md` (D13).

## Modelo de datos

```
ProductGroup  (principio activo + marca + forma farmaceutica)
   |
   +-- Product (presentacion: CAJA / BLISTER / UNIDAD, precio, IGV)
   |      |
   |      +-- UnitConversion (factor hacia la presentacion menor)
   |      |
   |      +-- Lot (lote, vencimiento, costo, cantidad actual, bloqueo)
   |             |
   |             +-- StockMovement (ledger inmutable: +/-, motivo, referencia)
   |
   +-- Product ...
```

Una caja, un blister y una unidad son **SKUs distintos** del mismo
`ProductGroup`. Vender "1 caja" y "10 unidades" son lineas distintas, con
precios distintos y lotes distintos.

### El stock no se edita

`Lot.current_quantity` es una **cache** del ledger. La unica forma de cambiarla
es registrar un `StockMovement` a traves de `apps/inventory/services.py`:

```
apply_movement(lot, quantity_delta, movement_type, reference_type, reference_id, ...)
```

El libro de movimientos es append-only: no se actualiza ni se borra. Si la cache
y el ledger no coinciden, `python manage.py check_consistency` lo detecta y
`/api/v1/inventory/consistency/` lo reporta.

### Vencimientos y FEFO

- Un lote es vendible **hasta el final de su fecha de vencimiento** (hora de
  `America/Lima`) y se bloquea desde el dia siguiente.
- `sellable_lots(product)` devuelve lotes activos, no bloqueados y no vencidos,
  ordenados por vencimiento (FEFO) y luego por id.
- Al vender, el servicio toma cantidades del primer lote con stock y continua
  con el siguiente. Una linea puede quedar cubierta por varios lotes.

### Venta atomica

```
POST /api/v1/sales/
      |
      +-- validar permiso (CanSell) y payload
      +-- BEGIN
      |     +-- reservar numero de venta (fila bloqueada)
      |     +-- leer precios del servidor (ignorar precios del cliente)
      |     +-- asignar lotes FEFO
      |     +-- crear Sale, SaleItem, SaleItemLot, Payment
      |     +-- registrar StockMovement de salida por cada lote
      |     +-- descontar Lot.current_quantity
      |     +-- auditar SALE_CREATED
      |   COMMIT
      +-- 201 con la venta completa
```

Si cualquier paso falla (stock insuficiente, lote vencido, pago invalido) la
transaccion completa se revierte. El carrito del cajero se conserva en pantalla
para corregir.

`client_request_id` (UUID) hace la operacion idempotente: el mismo UUID devuelve
la venta ya creada con `200` en lugar de duplicarla. El frontend genera uno por
intento logico y lo reutiliza al reintentar.

## Autenticacion

- Cookie de sesion `HttpOnly` + `SameSite=Lax`; no hay JWT.
- El login exige CSRF: el frontend llama primero a `GET /api/v1/auth/csrf/`.
- Cerrar sesion es del lado del servidor: desactivar una cuenta revoca el acceso
  de inmediato.
- Contrasenas con los validadores de Django. `must_change_password` fuerza el
  cambio en el primer ingreso o tras un restablecimiento.
- Login limitado a 10 intentos por minuto por IP (throttling de DRF).

## Dinero y cantidades

- Dinero en `Decimal`, jamas `float`. Precios con IGV incluido (18% por
  defecto, configurable por producto).
- Cantidades enteras: no hay ventas de media caja. El fraccionamiento convierte
  una presentacion en otra y genera dos movimientos (salida de la caja, entrada
  de las unidades).
- El frontend puede sumar el carrito en centavos **solo para mostrar**; el total
  que vale es el que devuelve el servidor.

## Frontend

```
src/
  app/          router, providers, layout, guards, navegacion
  api/          cliente HTTP (CSRF, errores) y endpoints tipados
  features/     auth | pos | sales | inventory | catalog | dashboard | users | audit
  components/   UI reutilizable (Button, Field, Table, Modal, ...)
  lib/          formato de dinero/fechas, carrito, hooks, ids
  test/         MSW + setup de Vitest
```

- La sesion vive en un contexto de React (`AuthProvider`), no en la cache de
  TanStack Query: es estado de identidad, no datos de servidor.
- TanStack Query maneja listados, dashboard y mutaciones; no hay Redux.
- El menu y las rutas se filtran por `capabilities` que devuelve `/auth/me/`.
  Es comodidad, no seguridad: el backend vuelve a verificar cada peticion.
- Dinero con `Intl.NumberFormat("es-PE", "PEN")`; fechas en `dd/mm/yyyy` con
  `America/Lima`.

## Pruebas

| Nivel | Herramienta | Que cubre |
|---|---|---|
| Backend unitario e integracion | pytest + pytest-django + factory-boy | servicios, API, transacciones |
| Concurrencia | pytest + transacciones reales | dos cajeros vendiendo el mismo lote |
| Matriz de permisos | pytest | 5 roles x cada endpoint + recorrido de rutas |
| Frontend | Vitest + Testing Library + MSW | login, POS, carrito, formato |

Las pruebas del backend corren **contra PostgreSQL**, nunca SQLite: SQLite no
reproduce el bloqueo de filas ni las restricciones que sostienen la venta.
