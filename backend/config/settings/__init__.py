"""Paquete de configuracion de my-pos.

El modulo de settings se selecciona por entorno con DJANGO_SETTINGS_MODULE:

    config.settings.dev    desarrollo local
    config.settings.prod   produccion

Ninguno de estos modulos contiene secretos: todo se lee de variables de entorno.
"""
