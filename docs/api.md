# API v1

Base: `/api/v1/`. Todas las respuestas son JSON. Los montos viajan como texto
(`"12.00"`) para no perder precision al pasar por `float`.

## Autenticacion

Cookie de sesion `HttpOnly` + token CSRF. No hay JWT. El flujo es:

1. `GET /auth/csrf/` — crea la cookie `csrftoken` y devuelve el token.
2. `POST /auth/login/` con `X-CSRFToken` — crea la sesion.
3. En cada `POST`, `PUT`, `PATCH` o `DELETE`, enviar `X-CSRFToken`.

```powershell
# PowerShell: iniciar sesion guardando cookies y token
$base = "http://localhost:8000/api/v1"
$csrf = (Invoke-RestMethod "$base/auth/csrf/" -SessionVariable s).csrfToken
$body = @{ username = "10000001"; password = "Farmacia2026" } | ConvertTo-Json
Invoke-RestMethod "$base/auth/login/" -Method Post -WebSession $s `
    -Headers @{ "X-CSRFToken" = $csrf } -ContentType "application/json" -Body $body
Invoke-RestMethod "$base/auth/me/" -WebSession $s
```

- `GET /auth/me/` devuelve el usuario y sus `capabilities`, que el frontend usa
  para armar el menu.
- `POST /auth/logout/` invalida la sesion en el servidor.
- `POST /auth/password/change/` con `{current_password, new_password}`.
- El login esta limitado a **10 intentos por minuto** por IP (responde 429).

Peticion sin sesion: `403` (`not_authenticated`), porque DRF no distingue sin
cabecera de autenticacion. Credenciales incorrectas en el login: `401`
(`authentication_failed`).

## Indice y panel navegable

`GET /api/v1/` devuelve un indice con las rutas principales agrupadas
(`autenticacion`, `usuarios`, `catalogo`, `inventario`, `ventas`, `reportes`,
`auditoria`). Requiere sesion, igual que el resto.

La misma API se puede recorrer desde el navegador con el **panel navegable de
DRF** (disponible tambien en produccion):

- Entra a `https://my-pos-api-2g1o.onrender.com/api/v1/` (o a
  `https://pharmacy-pos-gamma.vercel.app/api/v1/`) y usa el enlace *Log in*
  (`/api-auth/login/`); el usuario es el **DNI** y la contrasena la de la
  aplicacion. Es la misma sesion, sin *tokens* aparte.
- Ese login conserva las defensas de la API: 10 intentos por minuto por IP y
  eventos de auditoria `LOGIN_SUCCESS` / `LOGIN_FAILED` / `LOGOUT`.
- El panel solo cambia la representacion: no relaja permisos ni CSRF. Las
  escrituras desde el formulario necesitan la cookie `csrftoken`.
- Funciona con estilos en ambos dominios: Vercel reenvia `/api/*`, `/api-auth/*`
  y `/static/*` a Render.
- Los clientes siguen recibiendo JSON: `JSONRenderer` va primero y el navegable
  solo responde a `Accept: text/html`.

## Formato de error

```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "No hay stock suficiente para completar la operacion.",
    "details": { "product_id": 12, "requested": 3, "available": 1 }
  }
}
```

| Codigo | HTTP | Cuando |
|---|---|---|
| `validation_error` | 400 | payload invalido (`details` trae el detalle por campo) |
| `authentication_failed` | 401 | credenciales incorrectas en el login |
| `not_authenticated` | 403 | no hay sesion |
| `permission_denied` | 403 | el rol no permite la accion |
| `not_found` | 404 | el recurso no existe |
| `method_not_allowed` | 405 | metodo no soportado |
| `insufficient_stock` | 409 | stock vendible insuficiente |
| `lot_expired` | 409 | el lote esta vencido |
| `lot_blocked` | 409 | el lote esta bloqueado |
| `lot_expiry_mismatch` | 409 | el lote ya existe con otro vencimiento |
| `invalid_conversion` | 409 | no hay conversion entre presentaciones |
| `product_not_available` | 409 | producto inexistente o inactivo |
| `insufficient_payment` | 409 | el monto recibido es menor que el total |
| `payment_mismatch` | 409 | el monto no coincide con el total |
| `missing_query` | 400 | en `lookup` no se envio ni `q` ni `barcode` |
| `invalid_parameter` | 400 | un parametro de consulta tiene formato invalido |
| `throttled` | 429 | demasiados intentos (`details.retry_after_seconds`) |
| `error` | 500 | error inesperado (nunca expone el detalle interno) |

## Listados, filtros y paginacion

Los listados devuelven un sobre paginado:

```json
{ "count": 42, "next": "…?page=2", "previous": null, "results": [] }
```

Parametros comunes: `?page=`, `?page_size=` (maximo 100), `?search=`,
`?ordering=campo` o `?ordering=-campo`.

## Roles

| Rol | Puede |
|---|---|
| `ADMIN` | todo, incluida gestion de usuarios y consistencia |
| `REGENTE` | ventas, inventario, catalogo, dashboard, ajustes |
| `CAJERO` | vender y ver **sus propias** ventas |
| `ALMACEN` | inventario y catalogo (entradas, fraccionamiento) |
| `AUDITOR` | ver inventario, ventas de todos y auditoria (solo lectura) |

## Autenticacion y usuarios

| Metodo | Ruta | Rol |
|---|---|---|
| GET | `/auth/csrf/` | publico |
| POST | `/auth/login/` | publico (10/min) |
| POST | `/auth/logout/` | autenticado |
| GET | `/auth/me/` | autenticado |
| POST | `/auth/password/change/` | autenticado |
| GET | `/roles/` | autenticado |
| GET, POST | `/users/` | ADMIN |
| GET, PATCH | `/users/{id}/` | ADMIN |
| POST | `/users/{id}/deactivate/` | ADMIN |
| POST | `/users/{id}/role/` | ADMIN |
| POST | `/users/{id}/reset-password/` | ADMIN |

`POST /users/`:

```json
{
  "username": "10000007",
  "first_name": "Luis",
  "last_name": "Ramos",
  "email": "",
  "role": "CAJERO",
  "password": "clave-temporal",
  "must_change_password": true
}
```

Las cuentas no se eliminan: `deactivate` marca `is_active=false` y revoca la
sesion de inmediato.

## Catalogo

Lectura: cualquier usuario autenticado. Escritura: `ADMIN`, `REGENTE`, `ALMACEN`.

| Metodo | Ruta | Notas |
|---|---|---|
| GET | `/products/lookup/?q=` | busqueda para el POS: producto + stock vendible + proximo lote |
| GET | `/products/lookup/?barcode=` | por codigo de barras (404 si no existe) |
| GET | `/products/low-stock/` | productos bajo su stock minimo |
| GET | `/products/{id}/lots/` | lotes del producto |
| CRUD | `/products/`, `/product-groups/`, `/laboratories/`, `/categories/`, `/active-ingredients/`, `/unit-conversions/` | catalogos |

Respuesta de `lookup` (arreglo):

```json
[
  {
    "id": 12,
    "display_name": "Paracetamol 500 mg - Caja x 100",
    "barcode": "7751234500011",
    "presentation": "CAJA",
    "presentation_display": "Caja",
    "sale_price": "12.00",
    "tax_rate": "18.00",
    "last_cost": "8.0000",
    "stock": 10,
    "lots": [
      { "id": 7, "batch_number": "L-2601", "expiry_date": "2027-01-27", "quantity": 10 }
    ]
  }
]
```

`stock` es **vendible**: excluye lotes vencidos y bloqueados.

## Inventario

| Metodo | Ruta | Rol |
|---|---|---|
| GET | `/stock-entries/` | ADMIN, REGENTE, ALMACEN |
| POST | `/stock-entries/` | ADMIN, REGENTE, ALMACEN |
| POST | `/stock-adjustments/` | ADMIN, REGENTE |
| POST | `/stock-fractionations/` | ADMIN, REGENTE, ALMACEN |
| GET | `/stock-movements/` | ADMIN, REGENTE, ALMACEN, AUDITOR |
| GET | `/lots/` | ADMIN, REGENTE, ALMACEN, AUDITOR |
| GET | `/lots/expiring/?within_days=90` | ADMIN, REGENTE, ALMACEN, AUDITOR |
| GET | `/lots/expired/` | ADMIN, REGENTE, ALMACEN, AUDITOR |
| POST | `/lots/{id}/block/` | ADMIN, REGENTE, ALMACEN |
| GET | `/inventory/consistency/` | ADMIN |

Entrada de mercaderia (`client_request_id` obligatorio):

```json
{
  "client_request_id": "5f1c9b1e-3a5f-4d0a-9c3e-2b8f0d1a7c44",
  "supplier": "Drogueria del Norte",
  "document_number": "F001-12345",
  "received_at": "2026-10-19",
  "items": [
    {
      "product": 12,
      "batch_number": "L-2601",
      "expiry_date": "2027-01-27",
      "quantity": 20,
      "cost_price": "8.0000"
    }
  ]
}
```

Un mismo lote repetido dentro de la entrada se rechaza: se suman las cantidades
en una sola linea.

Ajuste de stock. `movement_type` es `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`,
`BAJA_VENCIMIENTO` o `BAJA_AVERIA`; el motivo es obligatorio.

```json
{
  "lot": 7,
  "quantity_delta": -2,
  "movement_type": "BAJA_AVERIA",
  "reason": "Blister roto en vitrina",
  "notes": ""
}
```

Fraccionamiento: se abre un lote de la presentacion mayor y entra el lote de la
presentacion menor que tenga configurada la conversion. El servidor copia el
numero de lote y la fecha de vencimiento del origen (no se envian), y rechaza el
lote de origen si esta vencido o bloqueado (RF1-RF7, ver `docs/decisiones.md`).

```json
{
  "source_lot": 7,
  "quantity": 2,
  "reason": "Venta al detalle"
}
```

Errores posibles: `lot_expired`, `lot_blocked`, `insufficient_stock`,
`invalid_conversion`, `lot_expiry_mismatch`.

Bloqueo de lote:

```json
{ "reason": "Sospecha de cadena de frio" }
```

Los movimientos son inmutables: no hay `PATCH` ni `DELETE`.

## Ventas

| Metodo | Ruta | Rol |
|---|---|---|
| GET | `/sales/` | ADMIN, REGENTE, CAJERO, AUDITOR (cajero: solo las propias) |
| GET | `/sales/{id}/` | idem |
| POST | `/sales/` | ADMIN, REGENTE, CAJERO |
| GET | `/sales/{id}/receipt/` | idem lectura |
| GET | `/receipts/{number}/` | idem lectura |

Filtros: `?status=`, `?date_from=2026-10-01&date_to=2026-10-19`, `?search=00000042`.

Peticion:

```json
{
  "client_request_id": "9c1f0e22-8b4d-4d1e-9a77-6f2e3b4c5d6e",
  "items": [{ "product_id": 12, "quantity": 2 }],
  "payment": { "method": "EFECTIVO", "received_amount": "50.00", "reference": "" },
  "notes": ""
}
```

- El cliente **no envia precios**: los pone el servidor y quedan congelados en
  la venta.
- `method` es `EFECTIVO`, `TARJETA` o `TRANSFERENCIA`.
- `received_amount` es obligatorio en efectivo (para calcular el vuelto); en
  tarjeta y transferencia se omite.
- Respuesta `201` con la venta completa. Si el `client_request_id` se repite,
  responde `200` con la venta ya existente y `X-Idempotent-Replay: true`.

Respuesta (resumida):

```json
{
  "id": 42,
  "number": "00000042",
  "status": "CONFIRMADA",
  "status_display": "Confirmada",
  "total": "24.00",
  "seller_name": "Rosa Quispe",
  "created_at": "2026-10-19T10:15:00-05:00",
  "notes": "",
  "created_by": 3,
  "items": [
    {
      "id": 90,
      "product": 12,
      "product_name": "Paracetamol 500 mg - Caja x 100",
      "quantity": 2,
      "unit_price": "12.00",
      "line_total": "24.00",
      "unit_cost": "8.0000",
      "margin": "8.00",
      "lot_allocations": [
        {
          "id": 55,
          "lot": 7,
          "batch_number": "L-2601",
          "expiry_date": "2027-01-27",
          "quantity": 2,
          "unit_cost": "8.0000"
        }
      ]
    }
  ],
  "payments": [
    {
      "id": 42,
      "method": "EFECTIVO",
      "method_display": "Efectivo",
      "amount": "24.00",
      "received_amount": "50.00",
      "change_amount": "26.00",
      "reference": ""
    }
  ]
}
```

### Boleta

`GET /receipts/{number}/` devuelve **solo lo que va en el papel**: nombre del
producto, cantidad, precio unitario, importe, total y pago. No incluye costo,
margen, ids internos ni datos de lote.

```json
{
  "number": "00000042",
  "created_at": "2026-10-19T10:15:00-05:00",
  "seller_name": "Rosa Quispe",
  "items": [
    {
      "product_name": "Paracetamol 500 mg - Caja x 100",
      "quantity": 2,
      "unit_price": "12.00",
      "line_total": "24.00"
    }
  ],
  "total": "24.00",
  "payment": {
    "method": "Efectivo",
    "amount": "24.00",
    "received_amount": "50.00",
    "change_amount": "26.00",
    "reference": ""
  }
}
```

## Reportes

| Metodo | Ruta | Rol |
|---|---|---|
| GET | `/reports/dashboard/` | ADMIN, REGENTE |
| GET | `/reports/sales-summary/?date_from=&date_to=` | ADMIN, REGENTE |
| GET | `/reports/top-products/?limit=` | ADMIN, REGENTE |
| GET | `/reports/exports/sales.csv` | ADMIN, REGENTE |
| GET | `/reports/exports/movements.csv` | ADMIN, REGENTE, ALMACEN, AUDITOR |

Los CSV se exportan con separador `;` y BOM UTF-8, para abrirlos directo en
Excel en espanol.

## Auditoria

| Metodo | Ruta | Rol |
|---|---|---|
| GET | `/audit-events/` | ADMIN, AUDITOR |
| GET | `/meta/` | autenticado |

`/audit-events/` filtra por `?action=`, `?actor=`, `?entity_type=`,
`?date_from=`, `?date_to=` y busca por `?search=`. No admite escritura: el
registro es inmutable.
