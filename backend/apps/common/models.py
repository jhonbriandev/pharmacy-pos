"""Modelos abstractos compartidos por todas las aplicaciones."""

from django.db import models


class TimeStampedModel(models.Model):
    """Agrega marcas de creacion y ultima modificacion.

    Se usa en modelos que representan estado mutable (productos, usuarios).
    Los registros que deben ser inmutables (movimientos, auditoria) NO lo usan:
    exponer un ``updated_at`` invitaria a editarlos.
    """

    created_at = models.DateTimeField("creado el", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = "created_at"
