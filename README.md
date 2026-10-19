# my-pos

Punto de venta e inventario para farmacia: ventas, entradas y salidas de
medicamentos con trazabilidad por lote y fecha de vencimiento, gestion de
inventario, autenticacion por roles y dashboard para gerencia.

- **Contexto:** una sola sucursal, un solo almacen, Peru.
- **Moneda:** Soles (S/). **Impuestos:** precios con IGV incluido.
- **Idioma:** espanol (Peru). **Fechas:** dd/mm/yyyy.

---

## Estado del proyecto

| Fase | Estado |
|---|---|
| 1. Preparacion del entorno | listo |
| 2. Configuracion del backend | listo |
| 3. Modelos y migraciones | listo |
| 4. API y autenticacion | listo |
| 5. Frontend | listo |
| 6. Integraciones externas | no aplica al MVP (sin pasarela de pago ni correo) |
| 7. Pruebas y seguridad | listo |
| 8. Despliegue | configurado (Render + Vercel) |
| 9. Documentacion final | listo |

Pendiente de confirmar con la farmacia y su contador el tratamiento tributario
de las boletas. Hasta entonces rige el IGV del 18%, incluido en el precio de
venta. Las reglas de fraccionamiento (RF1-RF7) ya estan fijadas y documentadas
en `docs/decisiones.md` (D19).

---

## Stack

| Capa | Tecnologia |
|---|---|
| Backend | Python 3.13 + Django 5.2 LTS + Django REST Framework |
| Base de datos | PostgreSQL 18 |
| Frontend | React 19 + Vite + JavaScript (JSX) |
| Estilos | Tailwind CSS 4 |
| Estado de servidor | TanStack Query |
| Pruebas backend | pytest + pytest-django + factory-boy |
| Pruebas frontend | Vitest + Testing Library + MSW |
| Formato frontend | Prettier |
| Servidor de aplicacion | Gunicorn (solo en Linux/produccion) |
| Despliegue | backend en Render, frontend en Vercel |

---

## Requisitos previos

- **Python 3.13** (recomendado desde <https://www.python.org/downloads/>, no la version de Microsoft Store)
- **Node.js 24** y npm
- **PostgreSQL 18** en ejecucion en `localhost:5432`
- **git**

Verifica con:

```powershell
python --version
node --version
git --version
psql --version
```

---

## Puesta en marcha (Windows / PowerShell)

### 1. Crear la base de datos

Desde la raiz del repositorio:

```powershell
psql -U postgres -h localhost -f scripts/setup_db.sql
```

El script crea el rol `mypos_app` y la base `mypos_dev`, y te pedira la
contrasena del rol de forma interactiva. No contiene ninguna contrasena.

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Crea el archivo de entorno y ajusta la contrasena de la base de datos:

```powershell
Copy-Item .env.example .env
notepad .env
```

Aplica migraciones y carga datos de prueba ficticios:

```powershell
python manage.py migrate
python manage.py seed
```

Arranca el servidor de desarrollo:

```powershell
python manage.py runserver
```

`seed` crea usuarios ficticios con la contrasena `Farmacia2026`:

| DNI | Rol |
|---|---|
| `10000001` | Administrador |
| `10000002` | Regente |
| `10000003` / `10000004` | Cajero |
| `10000005` | Almacen |
| `10000006` | Auditor |

**Los datos son ficticios.** Esta prohibido usar datos reales de pacientes o
clientes.

### 3. Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abre <http://localhost:5173>.

---

## Comandos utiles

### Backend (dentro de `backend/` con el entorno virtual activado)

| Comando | Para que sirve |
|---|---|
| `python manage.py runserver` | servidor de desarrollo |
| `python manage.py migrate` | aplicar migraciones |
| `python manage.py makemigrations` | generar migraciones nuevas |
| `python manage.py seed` | cargar datos ficticios de demostracion |
| `python manage.py create_admin --dni 12345678` | crear la cuenta administradora de arranque |
| `python manage.py check_consistency` | comparar el stock con el libro de movimientos |
| `pytest` | ejecutar las pruebas |
| `pytest --cov` | pruebas con cobertura |
| `ruff check .` | analisis estatico |
| `ruff format .` | formateo |

### Frontend (dentro de `frontend/`)

| Comando | Para que sirve |
|---|---|
| `npm run dev` | servidor de desarrollo con proxy a la API |
| `npm run build` | compilacion de produccion |
| `npm run test` | pruebas unitarias |
| `npm run lint` | analisis estatico |
| `npm run format` | formatear con Prettier |

---

## Pruebas

```powershell
cd backend
.\\.venv\\Scripts\\python.exe -m pytest --reuse-db

cd ..\\frontend
npm run test
```

- Backend: 248 pruebas que cubren servicios, API, transacciones, concurrencia
  (dos cajeros sobre el mismo lote), la matriz de 5 roles por endpoint y un
  recorrido que exige que cada ruta quede cubierta por un permiso explicito.
- Frontend: pruebas de login, POS (precio del servidor, reintento idempotente,
  falta de stock) y formato de dinero y fechas.
- El backend se prueba **contra PostgreSQL**, nunca SQLite: la correccion de las
  ventas depende de transacciones y bloqueo de filas reales.

---

## Despliegue

| Pieza | Donde | Configuracion |
|---|---|---|
| Backend | Render | `render.yaml` (Blueprint) |
| Base de datos | Render o Neon | `DATABASE_URL` |
| Frontend | Vercel | `frontend/vercel.json` (rewrite de `/api` al backend) |

El navegador ve un solo origen: Vercel reenvia `/api/*` a Render, asi que la
cookie de sesion viaja sin CORS ni `SameSite=None`. El paso a paso y la lista
de variables estan en `docs/operacion.md`.

---

## Documentacion

| Documento | Contenido |
|---|---|
| `docs/arquitectura.md` | diseno del sistema y diagramas |
| `docs/decisiones.md` | decisiones tecnicas y riesgos aceptados |
| `docs/api.md` | endpoints, roles y errores |
| `docs/manual-usuario.md` | guia para el personal de la farmacia |
| `docs/operacion.md` | respaldos, despliegue y que hacer si algo falla |

---

## Seguridad

- Ningun secreto se versiona: `.env` esta en `.gitignore` y solo se publica `.env.example`.
- El backend es la unica autoridad: los permisos, los precios y el stock se
  validan en el servidor, nunca en el navegador.
- Los datos de `seed` son **ficticios**. Esta prohibido usar datos reales de
  pacientes o clientes en desarrollo y pruebas.
