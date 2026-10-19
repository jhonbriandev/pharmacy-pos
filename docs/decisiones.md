# Decisiones tecnicas

Cada decision registra el contexto, lo que se eligio y lo que se acepta como
consecuencia. Si una decision cambia, se agrega una nueva entrada; no se reescribe
la historia.

---

## D1. Django 5.2 LTS en lugar de 6.x

**Contexto.** El proyecto necesita una version soportada por las dependencias
(DRF, django-filter, django-environ, whitenoise).

**Decision.** Fijar Django 5.2 LTS (`~=5.2.0`).

**Consecuencia.** Se reciben parches de seguridad de la rama 5.2, pero no las
novedades de 6.x. Actualizar de version mayor es una tarea aparte, con pruebas.

---

## D2. PostgreSQL 18, nunca SQLite

**Contexto.** La correccion del sistema depende de transacciones, bloqueo de
filas y restricciones que SQLite no reproduce igual.

**Decision.** PostgreSQL en desarrollo, pruebas y produccion.

**Consecuencia.** El entorno local necesita un PostgreSQL corriendo (ver
`scripts/setup_db.sql`). A cambio, una prueba de concurrencia local dice algo
real sobre produccion.

---

## D3. Sesion con cookie en lugar de JWT

**Contexto.** Un punto de venta se usa en un navegador de mostrador y la cuenta
puede desactivarse en cualquier momento.

**Decision.** Cookie de sesion `HttpOnly`, `SameSite=Lax`, con CSRF obligatorio.
Sin JWT.

**Consecuencia.** Cerrar sesion y desactivar una cuenta surten efecto de
inmediato en el servidor. Cuesta una peticion previa (`/auth/csrf/`), que el
cliente hace al arrancar.

---

## D4. Ledger de movimientos + cache de cantidad

**Contexto.** Se necesita saber no solo cuanto hay, sino por que cambio, y
auditar diferencias.

**Decision.** `StockMovement` es la fuente de verdad (append-only).
`Lot.current_quantity` es una cache que solo escribe
`apps/inventory/services.py`.

**Consecuencia.** Dos escrituras por movimiento, pero cada unidad tiene historia
y `check_consistency` detecta desvios. Ninguna vista ni serializer toca la
cantidad directamente.

---

## D5. Cantidades enteras y presentaciones como SKUs

**Contexto.** Una farmacia vende cajas, blisters y unidades del mismo producto a
precios distintos.

**Decision.** Cada presentacion es un `Product` propio dentro de un
`ProductGroup`. `UnitConversion` define el factor (por ejemplo, 1 caja = 10
blisters). No hay cantidades fraccionarias.

**Consecuencia.** El fraccionamiento es una operacion explicita que genera dos
movimientos. El POS no tiene que lidiar con decimales de cantidad.

---

## D6. Dinero con `Decimal` e IGV incluido

**Contexto.** Redondear con `float` produce centavos fantasma en boletas.

**Decision.** `Decimal` en toda la cadena; precios de venta con IGV incluido.

**Consecuencia.** El frontend usa centavos enteros solo para mostrar el carrito;
el total definitivo lo calcula el backend. La tasa es el 18% y no se configura
por producto (ver D20).

---

## D7. Auditoria propia e inmutable

**Contexto.** `django-simple-history` no declara soporte para las versiones
objetivo y aqui solo hacen falta acciones sensibles, no cada cambio de campo.

**Decision.** Modelo `AuditEvent` con `save()` que rechaza actualizaciones y
`delete()` que rechaza borrados. Una accion por evento, con estado anterior y
posterior en JSON.

**Consecuencia.** La inmutabilidad es explicita y esta probada. Si se necesita
historial completo de un modelo, se evalua otra herramienta.

---

## D8. Usuario propio con el DNI como nombre de usuario

**Contexto.** En Peru el DNI es el identificador natural del personal y evita
inventar nombres de usuario.

**Decision.** `User.username` es el DNI de 8 digitos. El correo es opcional.

**Consecuencia.** No se puede cambiar el DNI de una cuenta (seria otra persona).
El alta valida exactamente 8 digitos y el login muestra mensajes genericos.

---

## D9. FEFO y vencimiento inclusivo

**Contexto.** Un lote vence "el 27/01/2027": ese dia aun se puede vender.

**Decision.** FEFO (primero en vencer, primero en salir). Un lote es vendible
hasta el final de su fecha en `America/Lima` y se bloquea al dia siguiente.

**Consecuencia.** Las comparaciones se hacen por fecha local, no UTC. El
frontend parsea `AAAA-MM-DD` como fecha local (`parseDate`) para no mostrar el
dia anterior.

---

## D10. Idempotencia con `client_request_id`

**Contexto.** El mostrador tiene red inestable y el cajero hace doble clic.

**Decision.** Ventas y entradas de mercaderia exigen un UUID generado por el
cliente. El backend devuelve la operacion existente si el UUID se repite.

**Consecuencia.** Reintentar es seguro, pero el cliente debe **reutilizar** el
UUID al reintentar el mismo intento logico. El POS lo hace; un UUID nuevo por
clic anula la garantia.

---

## D11. El cajero ve solo sus ventas

**Contexto.** Privacidad del personal y auditoria sin exponer todo el historial
a cualquiera.

**Decision.** El listado de ventas filtra por vendedor cuando el rol es
`CAJERO`. `ADMIN`, `REGENTE` y `AUDITOR` ven todo. El permiso `SalesAccess`
separa lectura (incluye `AUDITOR`) de escritura (sin `AUDITOR`).

**Consecuencia.** Un auditor puede revisar ventas sin poder registrarlas. El
filtro es del servidor; ocultar el menu no es suficiente.

---

## D12. Un solo origen en produccion

**Contexto.** Cookies `SameSite=Lax` no viajan entre dominios distintos
(`vercel.app` -> `onrender.com`).

**Decision.** Vercel reescribe `/api/*` hacia Render (`frontend/vercel.json`).

**Consecuencia.** El navegador ve un solo origen: no hay CORS ni cookies
cruzadas. El destino del rewrite debe actualizarse cuando cambie el dominio del
backend. Plan B: `SameSite=None`, `Secure` y CORS con credenciales.

---

## D13. `catalog` importa servicios de `inventory` (desvio)

**Contexto.** El POS necesita, en una sola respuesta, producto + stock vendible
+ proximo lote. Esa logica (FEFO, bloqueos, vencimientos) vive en `inventory`.

**Decision.** Permitir que `catalog` importe `inventory.services` en tres vistas
de consulta (`lookup`, `low-stock`, `{id}/lots`). En sentido contrario sigue
prohibido.

**Consecuencia.** Se evita duplicar FEFO. El acoplamiento es de lectura y esta
acotado a esas vistas; cualquier escritura sigue pasando por `inventory`.

---

## D14. Numero de venta con fila bloqueada

**Contexto.** Dos cajeros pueden cobrar en el mismo instante.

**Decision.** `_next_sale_number()` bloquea la fila de `SaleNumberSequence`
dentro de la transaccion de la venta.

**Consecuencia.** Se serializa la numeracion (correctitud sobre rendimiento).
Con una sola sucursal y un solo almacen, el costo es despreciable.

---

## D15. Fuera del MVP: turnos, anulaciones, devoluciones y descuentos

**Contexto.** El alcance acordado es una sucursal, un almacen y ventas directas.

**Decision.** No hay cierre de caja ni arqueo, no se anulan ventas ni se aceptan
devoluciones, no hay descuentos por linea ni globales.

**Consecuencia.** El modelo deja espacio (`SaleStatus`) pero la API no expone
esas operaciones. Si se agregan, requieren movimientos de entrada y auditoria
propios.

---

## D16. Modulo de settings solo para pruebas

**Contexto.** El hasher por defecto encarece cada login de prueba y la suite
completa tardaba minutos.

**Decision.** `config/settings/test.py`: hasher MD5, sin throttling, renderer
solo JSON, almacenamiento en memoria.

**Consecuencia.** La suite baja a segundos. Ese modulo nunca se usa en
produccion (`prod.py` no lo importa).

---

## D17. Frontend en JavaScript y sin TypeScript

**Contexto.** El proyecto arranco con TypeScript, pero el equipo que mantiene la
farmacia no lo domina y la mayor parte del tiempo se perdia anotando tipos que la
API ya garantiza en tiempo de ejecucion. El contrato real (formas de las
respuestas, campos requeridos, codigos de error) vive en el backend y se prueba
con la suite de Django (`TestCase` / `APITestCase`).

**Decision.** Todo el frontend es JavaScript con JSX (`.js` / `.jsx`). No hay
`tsconfig.json`, ni `typescript`, ni `typescript-eslint`, ni paquetes `@types/*`.
El alias `@/*` se resuelve con `jsconfig.json` para el editor y con el alias de
Vite para el build. El estilo lo fija Prettier (`npm run format`).

**Consecuencia.** Menos herramientas y un build mas corto (`vite build`, sin
`tsc -b`). La sesion sigue viviendo en `AuthProvider` (contexto de React) y
TanStack Query se encarga de los datos de servidor. A cambio, un error de forma
en el frontend se detecta en las pruebas con MSW o en ejecucion, no al compilar.

---

## D18. Sin registro publico

**Contexto.** Es un sistema interno de farmacia; nadie debe crearse una cuenta
solo.

**Decision.** Las cuentas las crea un administrador desde la aplicacion. La
primera cuenta se crea en el servidor con `python manage.py create_admin`.

**Consecuencia.** No hay endpoint de registro. El `seed` con datos ficticios
solo corre con `DEBUG=True` (o con `--force` en un entorno de demostracion).

---

## D19. Reglas de fraccionamiento (RF1-RF7)

**Contexto.** El fraccionamiento (abrir una caja para vender blisters o
unidades sueltas) se presta a errores que rompen la trazabilidad por lote: abrir
un lote vencido, inventar un vencimiento nuevo para la presentacion menor o
duplicar lotes. La farmacia delego en el sistema la definicion de estas reglas.

**Decision.** Se fijan siete reglas y se implementan en
`apps/inventory/services.py::fractionate`, la unica puerta de entrada al stock:

| Regla | Enunciado |
|---|---|
| RF1 | Solo se fracciona un lote **vendible**: ni bloqueado ni vencido |
| RF2 | La conversion va de la presentacion mayor a la menor de `UnitConversion` (factor >= 2), dentro del mismo grupo, y la presentacion destino debe estar activa |
| RF3 | La cantidad es un entero mayor que cero y no supera el stock del lote de origen |
| RF4 | El lote destino **hereda** el numero de lote y el vencimiento del origen: no se piden al usuario |
| RF5 | Si el lote destino ya existe, se le suma la cantidad; no se crea un duplicado |
| RF6 | El costo unitario del destino es el del origen dividido por el factor |
| RF7 | Son **dos** movimientos en una transaccion (salida y entrada) y un evento de auditoria; un paso por operacion |

**Consecuencia.** El endpoint `/stock-fractionations/` solo recibe
`source_lot`, `quantity` y un `reason` opcional: el lote y el vencimiento no se
pueden falsear porque el servidor los copia del origen. Caja -> blister y
blister -> unidad son dos operaciones distintas, cada una auditada.

---

## D20. IGV fijo en 18%, incluido en el precio

**Contexto.** El precio de venta en la farmacia ya incluye el IGV y la boleta no
discrimina el impuesto. Tener una tasa editable por producto abria la puerta a
inconsistencias sin aportar nada al MVP.

**Decision.** El IGV es el **18%**, un valor unico del sistema. `Product.tax_rate`
se conserva como dato informativo (por si mas adelante se necesita exceptuar un
producto), pero la API lo expone como **solo lectura**: ni el alta ni la
edicion de un producto pueden cambiarlo. El formulario del catalogo ya no lo
pide.

**Consecuencia.** Todo producto queda en 18% hasta que exista un cambio
explicito (una migracion y una decision nuevas), no por descuido de quien captura
datos. Hay pruebas que lo verifican en `tests/test_api_catalog.py`.
