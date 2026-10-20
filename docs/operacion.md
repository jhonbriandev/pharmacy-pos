# Operacion

## Requisitos

| Herramienta | Version |
|---|---|
| Python | 3.13 |
| Node.js | 24 |
| PostgreSQL | 18 |

## Puesta en marcha local

### 1. Base de datos

```powershell
# Crea el usuario y la base (revisa el archivo antes de ejecutarlo)
psql -U postgres -f scripts\setup_db.sql
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

Copy-Item .env.example .env
# Edita .env: DATABASE_URL, DJANGO_SECRET_KEY y DJANGO_ALLOWED_HOSTS

python manage.py migrate
python manage.py seed          # datos ficticios de demostracion
python manage.py runserver     # http://localhost:8000
```

> En PowerShell 5.1, `Set-Content -Encoding utf8` escribe un BOM que rompe
> `django-environ`. Si editas `.env` por script, usa
> `[IO.File]::WriteAllText($ruta, $texto, [Text.UTF8Encoding]::new($false))`.

El `seed` crea usuarios ficticios con la contrasena `Farmacia2026`:

| DNI | Rol |
|---|---|
| `10000001` | ADMIN |
| `10000002` | REGENTE |
| `10000003` / `10000004` | CAJERO |
| `10000005` | ALMACEN |
| `10000006` | AUDITOR |

**Los datos son ficticios.** No se usan datos reales de clientes ni pacientes.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Vite reenvia `/api` a `http://localhost:8000`, asi que el navegador ve un solo
origen tambien en desarrollo.

## Pruebas

```powershell
# Backend (necesita PostgreSQL; --keepdb reutiliza la base de pruebas)
cd backend
python manage.py test --keepdb

# Frontend
cd frontend
npm run test
npm run lint
npm run build
```

La suite del backend corre con `config.settings.test` (hasher rapido, sin
throttling, renderer solo JSON); `manage.py test` lo selecciona solo. Nunca se
prueba contra SQLite.

## Variables de entorno

### Backend

| Variable | Por defecto | Descripcion |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | `dev`, `prod` o `test` |
| `DJANGO_SECRET_KEY` | — | **obligatoria**; en prod, generada por Render |
| `DJANGO_DEBUG` | `False` | `True` solo en desarrollo |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | hosts separados por coma |
| `DATABASE_URL` | — | **obligatoria**: `postgres://usuario:clave@host:puerto/base` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | vacio | dominios del frontend, con `https://` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | vacio | solo si se accede cruzando dominios |
| `DJANGO_USE_X_FORWARDED_PROTO` | `False` | `True` detras de un proxy TLS |
| `DJANGO_CONN_MAX_AGE` | `60` | segundos de conexion persistente |
| `DJANGO_TIME_ZONE` | `America/Lima` | zona del negocio |
| `DJANGO_LANGUAGE_CODE` | `es-pe` | idioma de la API |
| `DJANGO_LOG_LEVEL` | `INFO` | nivel de logging |

### Frontend

No necesita variables: llama a `/api/v1/` en su propio origen. El destino del
backend vive en `frontend/vercel.json` (rewrite), no en variables.

## Despliegue

### Despliegue continuo (GitHub Actions)

El pipeline esta en `.github/workflows/`:

- **`ci.yml`** corre en cada push y pull request hacia `main`/`develop`: lint,
  pruebas del backend contra PostgreSQL, `check --deploy` de seguridad y lint,
  pruebas y build del frontend.
- **`deploy.yml`** se dispara **solo si `ci.yml` termino en `success` sobre
  `main`**. Despliega con *deploy hooks* (si existen) y luego verifica que
  produccion responda: `/healthz`, el proxy `/api/v1/auth/csrf/` y la portada.
  El trabajo usa el entorno `production` de GitHub: deja historial de
  despliegues y permite exigir aprobacion manual (*Settings > Environments*)
  sin editar el workflow.

Para que sea Actions quien despliegue, crea los *deploy hooks* y guardalos como
secretos del repositorio (**Settings > Secrets and variables > Actions**):

| Secreto | Donde se obtiene |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | Render: servicio > *Settings* > *Deploy Hook* |
| `VERCEL_DEPLOY_HOOK_URL` | Vercel: proyecto > *Settings* > *Git* > *Deploy Hook* |

Opcionalmente define las variables `API_BASE_URL` y `WEB_BASE_URL` para apuntar
la verificacion a otros dominios.

Sin esos secretos, el workflow solo verifica produccion; del despliegue se
encargan las integraciones nativas de Git:

- **Vercel** despliega en cada push a su rama de produccion (`main`); se
  configura en *Settings > Git > Production Branch*.
- **Render** despliega en cada push a `main` (`autoDeploy: true` en
  `render.yaml`); si el servicio se creo a mano, activa *Settings > Build &
  Deploy > Auto-Deploy*.

Si usas los *deploy hooks*, apaga el Auto-Deploy nativo para no desplegar dos
veces por el mismo commit.

### Datos ficticios en produccion (demostracion)

Para probar la aplicacion desplegada, abre el **Shell** del servicio en Render y
ejecuta:

```bash
python manage.py seed --force
```

`--force` es obligatorio cuando `DEBUG=False`. Crea usuarios de todos los roles,
catalogo, lotes (uno vencido, para ver la alerta) y ventas de ejemplo. Es
idempotente y **nunca** cambia la contrasena ni el rol de una cuenta que ya
existe: solo fija la contrasena `Farmacia2026` en las cuentas que crea.

> Las cuentas de demostracion quedan con una contrasena conocida. Antes de
> cargar datos reales, desactivalas (no se borran): `is_active=False`.

### Backend en Render

1. Sube el repositorio a GitHub.
2. **New > Blueprint**, elige el repositorio. Render lee `render.yaml`.
3. Cuando lo pida, completa las variables marcadas como `sync: false`:
   - `DATABASE_URL` — cadena de conexion a PostgreSQL.
   - `DJANGO_CSRF_TRUSTED_ORIGINS` — `https://<tu-app>.vercel.app`.
   - `DJANGO_CORS_ALLOWED_ORIGINS` — el mismo dominio.
4. El build corre `collectstatic` y `migrate`; el arranque es
   `gunicorn config.wsgi:application`.
5. Verifica el arranque: `GET https://<tu-servicio>.onrender.com/healthz` debe
   responder `{"status": "ok"}` sin consultar la base.
6. Crea la primera cuenta desde **Shell**:

   ```bash
   python manage.py create_admin --dni 12345678 --first-name Ana --last-name Torres
   ```

   El comando pide la contrasena de forma interactiva y la valida. Es la unica
   cuenta con acceso a `/admin/`; las demas se crean desde la aplicacion.

Notas:

- En el plan gratuito la instancia se duerme por inactividad: el primer acceso
  del dia puede tardar ~50 segundos.
- `migrate` corre en el build. Con una sola instancia no hay carrera; si se
  escala a varias, muevelo a un job de despliegue.
- `seed` esta bloqueado con `DEBUG=False`: en produccion solo se usa
  `create_admin`.

### Base de datos

Opciones:

- **Render Postgres**: se crea desde el panel; usa la *Internal Connection
  String* si el backend vive en Render.
- **Neon**: cadena con `?sslmode=require`. Util para el plan gratuito.

La base no se aprovisiona en `render.yaml` a proposito: las gratuitas caducan y
es mejor decidir donde viven los datos de forma explicita.

### Frontend en Vercel

1. **Add New > Project**, importa el repositorio.
2. **Root Directory**: `frontend`.
3. Edita `frontend/vercel.json` y reemplaza el destino del rewrite por la URL
   real del backend:

   ```json
   { "source": "/api/(.*)", "destination": "https://tu-servicio.onrender.com/api/$1" }
   ```

   Usa `(.*)` y `$1`, **no** `:path*`: el patron `:path*` no casa con las rutas
   que terminan en barra (`/api/v1/auth/login/`), que son justamente las que
   usa el cliente, y Vercel responde su propio 404.

4. Despliega. El otro rewrite manda cualquier ruta al `index.html` para que el
   router del navegador funcione al recargar.
5. Agrega el dominio de Vercel a `DJANGO_CSRF_TRUSTED_ORIGINS` (y a
   `DJANGO_CORS_ALLOWED_ORIGINS`) en Render y vuelve a desplegar.

### Orden recomendado

1. Crear la base de datos.
2. Desplegar el backend y comprobar `/healthz`.
3. Crear la cuenta con `create_admin`.
4. Desplegar el frontend y ajustar el rewrite.
5. Registrar el dominio del frontend en Render y redesplegar.

## Respaldos

```powershell
# Respaldo completo
pg_dump "$env:DATABASE_URL" --no-owner --format=custom --file "respaldo_$(Get-Date -Format yyyyMMdd).dump"

# Restauracion
pg_restore --clean --no-owner --dbname "$env:DATABASE_URL" respaldo_20261019.dump
```

Los planes gratuitos no incluyen respaldos automaticos: programa un `pg_dump`
periodico o exporta los CSV de `/reports/exports/` como respaldo minimo. Un
respaldo que nunca se restauro no es un respaldo: prueba el procedimiento al
menos una vez antes de confiar en el.

## Diagnostico y mantenimiento

| Que | Como |
|---|---|
| Estado del servicio | `GET /healthz` (no consulta la base) |
| Version de la API | `GET /api/v1/meta/` (requiere sesion) |
| Coherencia de stock | `python manage.py check_consistency` o `GET /api/v1/inventory/consistency/` (ADMIN) |
| Registro de acciones | `/api/v1/audit-events/` en la interfaz de auditoria |
| Logs | panel de Render |

`check_consistency` compara `Lot.current_quantity` con la suma del libro de
movimientos. Cualquier diferencia es un incidente: se investiga en
`/audit-events/` y se corrige con un ajuste, nunca editando la cantidad a mano.

### Panel navegable de la API

La API de produccion incluye el panel navegable de DRF (ver D22). Para revisar
endpoints, campos y permisos desde el navegador:

1. Abre `https://my-pos-api-2g1o.onrender.com/api/v1/` (o
   `https://pharmacy-pos-gamma.vercel.app/api/v1/`; Vercel reenvia `/api/*`,
   `/api-auth/*` y `/static/*`, asi que el panel funciona igual en ambos).
2. *Log in* → `/api-auth/login/` con el **DNI** y la contrasena de la
   aplicacion. Es la misma sesion: no hay *tokens* aparte. El login tiene el
   mismo limite de 10 intentos por minuto por IP y deja eventos de auditoria.
3. `GET /api/v1/` es el indice; cada grupo enlaza sus colecciones.

El panel no relaja nada: exige sesion y rol, y las escrituras siguen pidiendo
`X-CSRFToken`.

## Seguridad

- `DJANGO_DEBUG` en `False` y `DJANGO_SECRET_KEY` distinta por entorno.
- HTTPS obligatorio, HSTS, `X-Frame-Options: DENY`, `nosniff`.
- Sesion `HttpOnly`; cierre de sesion del lado del servidor.
- Desactivar una cuenta revoca el acceso al instante (no se borra).
- Login limitado a 10 intentos por minuto por IP.
- Ningun secreto en el repositorio: solo `.env.example`.
- Si se filtra una clave: rotar `DJANGO_SECRET_KEY` (invalida las sesiones) y la
  contrasena de la base.

## Problemas comunes

| Sintoma | Causa probable | Solucion |
|---|---|---|
| `403` en cualquier `POST` | falta `X-CSRFToken` o la cookie no llego | llamar antes a `/auth/csrf/`; revisar `DJANGO_CSRF_TRUSTED_ORIGINS` |
| La sesion no persiste entre frontend y backend | dominios distintos sin rewrite | usar el rewrite de Vercel, no llamar a Render directo |
| Primer acceso lento en produccion | instancia gratuita dormida | es esperado; se activa al recibir trafico |
| `429` al iniciar sesion | throttling (10/min) | esperar un minuto |
| La app arranca sin leer `.env` | BOM al inicio del archivo | guardar `.env` como UTF-8 sin BOM |
| `Exited with code 1` sin mensaje | redireccion `2>&1` en PowerShell | ejecutar el comando sin redirigir la salida |

## Actualizar dependencias

```powershell
cd backend
.\\.venv\\Scripts\\python.exe -m pip install --upgrade -r requirements-dev.txt
python manage.py test --keepdb
.\\.venv\\Scripts\\python.exe -m ruff check .

cd ..\\frontend
npm outdated
npm update
npm run test && npm run build
```

Las versiones se fijan por rama menor (`~=`) para recibir parches sin saltos de
version mayor. Cualquier salto de version mayor requiere una entrada nueva en
`docs/decisiones.md`.
