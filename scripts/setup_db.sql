-- ---------------------------------------------------------------------------
--  my-pos :: preparacion de la base de datos local de desarrollo
--
--  Uso (una sola vez, desde la raiz del repositorio):
--      psql -U postgres -h localhost -f scripts/setup_db.sql
--
--  Que hace:
--    1. Crea el rol de aplicacion "mypos_app" (sin privilegios de superusuario).
--       Necesita CREATEDB para que Django pueda crear la base de datos de tests.
--    2. Crea la base de datos "mypos_dev" propiedad de ese rol, en UTF8.
--    3. Pide interactivamente la contrasena del rol (oculta, no se guarda en disco).
--
--  La contrasena que escribas aqui debe ir despues en backend/.env, dentro de
--  DATABASE_URL. Este archivo NO contiene ninguna contrasena.
-- ---------------------------------------------------------------------------

\set ON_ERROR_STOP on

\echo ''
\echo '==> 1/3  Creando rol de aplicacion mypos_app (si no existe)...'

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mypos_app') THEN
        CREATE ROLE mypos_app LOGIN CREATEDB;
        RAISE NOTICE 'Rol mypos_app creado.';
    ELSE
        RAISE NOTICE 'El rol mypos_app ya existia: no se modifica.';
    END IF;
END
$$;

\echo '==> 2/3  Creando base de datos mypos_dev (si no existe)...'

SELECT 'CREATE DATABASE mypos_dev OWNER mypos_app ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mypos_dev')
\gexec

\echo '==> 3/4  Definiendo la contrasena del rol mypos_app.'
\echo '    Se solicitara dos veces y no se mostrara en pantalla.'
\password mypos_app

\echo '==> 4/4  Verificacion...'

SELECT rolname, rolcanlogin, rolcreatedb, rolsuper
FROM pg_roles
WHERE rolname = 'mypos_app';

SELECT datname, pg_encoding_to_char(encoding) AS encoding, pg_get_userbyid(datdba) AS owner
FROM pg_database
WHERE datname = 'mypos_dev';

\echo ''
\echo 'Listo. Ahora copia la contrasena que definiste en backend/.env (DATABASE_URL).'
\echo 'Ejemplo:  postgres://mypos_app:TU_CONTRASENA@localhost:5432/mypos_dev'
\echo ''
