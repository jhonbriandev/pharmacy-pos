# Manual de uso

## Que es my-pos

El sistema de la farmacia: registro las ventas del mostrador, controla el
inventario por lote y vencimiento, y deja registro de quien hizo cada cosa.
Una sola sucursal, un solo almacen.

## Como entro

1. Abre la direccion del sistema en el navegador.
2. Escribe tu **DNI** (8 digitos, sin puntos) y tu contrasena.
3. Si es tu primer ingreso, el sistema te pedira cambiar la contrasena.

Si olvidaste la contrasena, un administrador te la restablece. Al restablecerla,
el sistema te pedira cambiarla la proxima vez que entres.

Puedes cerrar sesion desde el menu de tu nombre, arriba a la derecha. Cerrar
sesion es inmediato: nadie puede seguir usando tu cuenta.

## Tu rol y lo que puedes hacer

| Rol | En una frase |
|---|---|
| Administrador | todo el sistema, incluidos usuarios |
| Regente | ventas, inventario, catalogo, dashboard y ajustes |
| Cajero | vender y ver sus propias ventas |
| Almacen | inventario y catalogo (entradas, fraccionamiento, bloqueos) |
| Auditor | mirar: inventario, ventas de todos y auditoria |

El menu solo muestra lo que tu rol puede usar. Si algo no aparece, no es un
error: no tienes ese permiso.

## Punto de venta

1. Entra a **Punto de venta**.
2. Busca el producto por nombre (dos letras o mas) o pasa el **lector de codigo
   de barras**. Con el lector, presionar Enter agrega el producto directo.
3. Haz clic en el resultado para agregarlo al carrito. Cada linea muestra el
   precio y el stock disponible.
4. Ajusta la cantidad con los botones `+` y `-`, o quita la linea con la papelera.
   El sistema no deja pedir mas de lo que hay: el stock que se muestra es el
   **vendible** (sin lotes vencidos ni bloqueados).
5. Elige la forma de pago:
   - **Efectivo**: escribe lo que entrega el cliente y el sistema calcula el
     vuelto. El boton **Exacto** llena el monto justo.
   - **Tarjeta** o **Transferencia**: no se pide vuelto.
6. Presiona **Cobrar**. Si todo esta bien, se abre la **boleta** con el numero
   de venta.

La boleta se puede imprimir en una impresora termica de 80 mm. El sistema
guarda cada venta, asi que la boleta se puede volver a consultar desde
**Ventas**.

Detalles que conviene saber:

- Los precios los pone el sistema: no se pueden cambiar desde el mostrador.
- Si la red falla al cobrar, presiona **Cobrar** otra vez: la venta no se
  duplica, el sistema reconoce el reintento.
- Si falta stock, la venta no se registra y el carrito se conserva para que
  corrijas la cantidad.

## Ventas

- Los **cajeros** ven solo sus propias ventas.
- El **administrador**, el **regente** y el **auditor** ven las de todo el
  equipo.
- Filtra por rango de fechas y busca por numero de venta.
- Entra al detalle para ver los productos, los lotes que se usaron y el pago.
  Desde ahi se reimprime la boleta.

## Inventario

### Entrada de mercaderia

1. Entra a **Inventario > Nueva entrada**.
2. Completa proveedor y, si tienes, el numero de documento y la fecha de
   recepcion.
3. Agrega cada producto con su **lote**, **fecha de vencimiento**, cantidad y
   costo.
4. Guarda.

Un mismo lote no se repite dentro de la entrada: si recibiste en dos tandas,
suma las cantidades en una sola linea. Si el lote ya existia con otra fecha de
vencimiento, el sistema avisa: revisa el numero antes de continuar.

### Ajustes

Sirven para corregir el inventario cuando algo pasa fuera del sistema: rotura,
merma, conteo fisico. Siempre piden un **motivo** y quedan en el libro de
movimientos. Un ajuste no es una herramienta de uso diario: si ajustas seguido,
algo mas esta fallando.

Tipos: ajuste positivo, ajuste negativo, baja por vencimiento y baja por averia.

### Bloquear un lote

Si un lote deja de ser confiable (cadena de frio, sospecha), se bloquea. Un lote
bloqueado no se vende y deja de contar como stock disponible. El motivo es
obligatorio.

### Fraccionar

Abre una presentacion mayor (por ejemplo, una caja) y crea la menor (blisters o
unidades). La fecha de vencimiento se conserva del lote de origen. Hay que
elegir el lote de origen y cuantas unidades abrir.

### Vencimientos

La pantalla de inventario destaca los lotes por vencer y los vencidos:

- Un lote se puede vender **hasta el dia de su vencimiento, inclusive**.
- Al dia siguiente queda bloqueado solo.
- Los lotes vencidos con existencias aparecen aparte para darlos de baja.

## Catalogo

Aqui se administran laboratorios, categorias, principios activos, grupos y
productos.

- Un **grupo** agrupa las presentaciones del mismo producto (nombre,
  concentracion, forma farmaceutica).
- Cada **presentacion** (caja, blister, unidad) es un producto con su codigo de
  barras, su precio y su stock minimo.
- Las **conversiones** indican cuantas unidades menores tiene una mayor; son las
  que usa el fraccionamiento.
- El **stock minimo** alimenta el aviso de productos por agotarse.

Cada presentacion tiene su precio de venta (con IGV incluido) y su porcentaje de
IGV. Los cambios de precio quedan registrados en auditoria.

## Dashboard

Para gerencia y regencia. Muestra las ventas del periodo, los productos mas
vendidos, el valor del inventario y los lotes por vencer. Se puede exportar a
CSV para abrirlo en Excel.

## Usuarios

Solo el administrador. Desde aqui se crea una cuenta (DNI, nombre, rol y una
contrasena temporal), se cambia el rol, se restablece la contrasena y se
desactiva una cuenta.

- Las cuentas **no se borran**: se desactivan. Una cuenta desactivada no puede
  entrar y su historial se conserva.
- No puedes desactivar tu propia cuenta.
- Al crear una cuenta, el sistema pide cambiar la contrasena en el primer
  ingreso.

## Auditoria

Solo el administrador y el auditor. Es el registro de lo que paso y quien lo
hizo: inicios y cierres de sesion, intentos fallidos, ventas, entradas, ajustes,
bloqueos, cambios de precio y de rol.

Se filtra por accion, fecha y usuario. **No se puede editar ni borrar**: es la
razon por la que existe.

## Buenas practicas

- Cierra sesion al dejar el mostrador.
- No compartas tu DNI ni tu contrasena: todo lo que pasa con tu cuenta queda a
  tu nombre.
- Ante un error raro, anota el numero de venta o de lote antes de avisar: con
  eso se encuentra el caso en auditoria en segundos.
- Si el sistema muestra un error al cobrar, revisa el mensaje y corrige: no
  reintentes a ciegas ni registres la venta dos veces.
