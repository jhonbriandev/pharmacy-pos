"""Catalogo de medicamentos.

Un ``ProductGroup`` es el medicamento (nombre + concentracion + forma
farmaceutica) y agrupa varias presentaciones vendibles (``Product``): caja,
blister, unidad. Cada presentacion es un SKU con su propio stock, precio y
codigo de barras, porque fisicamente son inventarios distintos.

La conversion entre presentaciones vive en ``UnitConversion`` y se usa para el
fraccionamiento (abrir una caja y vender blisteres sueltos).
"""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class Laboratory(TimeStampedModel):
    name = models.CharField("nombre", max_length=120, unique=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "laboratorio"
        verbose_name_plural = "laboratorios"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Category(TimeStampedModel):
    name = models.CharField("nombre", max_length=120, unique=True)
    description = models.CharField("descripcion", max_length=250, blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ActiveIngredient(TimeStampedModel):
    name = models.CharField("nombre", max_length=120, unique=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "principio activo"
        verbose_name_plural = "principios activos"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PharmaceuticalForm(models.TextChoices):
    TABLET = "TABLETA", "Tableta"
    CAPSULE = "CAPSULA", "Capsula"
    SYRUP = "JARABE", "Jarabe"
    SUSPENSION = "SUSPENSION", "Suspension"
    SOLUTION = "SOLUCION", "Solucion"
    CREAM = "CREMA", "Crema"
    GEL = "GEL", "Gel"
    DROPS = "GOTAS", "Gotas"
    INJECTABLE = "INYECTABLE", "Inyectable"
    SUPPOSITORY = "SUPOSITORIO", "Supositorio"
    POWDER = "POLVO", "Polvo"
    OINTMENT = "UNGUENTO", "Unguento"
    OTHER = "OTRO", "Otro"


class PresentationType(models.TextChoices):
    BOX = "CAJA", "Caja"
    BLISTER = "BLISTER", "Blister"
    UNIT = "UNIDAD", "Unidad"
    BOTTLE = "FRASCO", "Frasco"
    TUBE = "TUBO", "Tubo"
    AMPOULE = "AMPOLLA", "Ampolla"
    SACHET = "SOBRE", "Sobre"
    OTHER = "OTRO", "Otro"


class ProductGroup(TimeStampedModel):
    """Medicamento comercial: agrupa sus presentaciones vendibles."""

    name = models.CharField("nombre comercial", max_length=160, db_index=True)
    concentration = models.CharField("concentracion", max_length=60)
    pharmaceutical_form = models.CharField(
        "forma farmaceutica",
        max_length=20,
        choices=PharmaceuticalForm.choices,
        default=PharmaceuticalForm.TABLET,
    )
    laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.PROTECT,
        related_name="product_groups",
        verbose_name="laboratorio",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="product_groups",
        verbose_name="categoria",
        null=True,
        blank=True,
    )
    ingredients = models.ManyToManyField(
        ActiveIngredient,
        related_name="product_groups",
        verbose_name="principios activos",
        blank=True,
    )
    notes = models.CharField("notas", max_length=250, blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "grupo de productos"
        verbose_name_plural = "grupos de productos"
        ordering = ["name", "concentration"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "concentration", "pharmaceutical_form", "laboratory"],
                name="unique_product_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.concentration}".strip()

    @property
    def display_name(self) -> str:
        return f"{self.name} {self.concentration} ({self.get_pharmaceutical_form_display()})"


class Product(TimeStampedModel):
    """Presentacion vendible (SKU): caja, blister o unidad de un medicamento."""

    group = models.ForeignKey(
        ProductGroup,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="grupo",
    )
    presentation = models.CharField(
        "presentacion",
        max_length=20,
        choices=PresentationType.choices,
        default=PresentationType.BOX,
    )
    presentation_detail = models.CharField(
        "detalle de presentacion",
        max_length=60,
        blank=True,
        help_text="Por ejemplo: 'x 100', 'x 10', 'frasco 120 ml'.",
    )
    barcode = models.CharField(
        "codigo de barras",
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Puede quedar vacio (por ejemplo, en unidades sueltas).",
    )
    unit_label = models.CharField(
        "unidad",
        max_length=20,
        blank=True,
        help_text="Unidad de conteo para mostrar: tableta, frasco, ampolla...",
    )
    sale_price = models.DecimalField(
        "precio de venta",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Precio final con IGV (18%) incluido.",
    )
    tax_rate = models.DecimalField(
        "tasa de IGV (%)",
        max_digits=5,
        decimal_places=2,
        default=18,
        validators=[MinValueValidator(0)],
        help_text="Solo informativo: el precio ya incluye el IGV del 18%.",
    )
    last_cost = models.DecimalField(
        "ultimo costo unitario",
        max_digits=12,
        decimal_places=4,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Costo de la ultima entrada. Lo actualiza el servicio de inventario.",
    )
    min_stock = models.PositiveIntegerField(
        "stock minimo",
        default=0,
        help_text="Cantidad a partir de la cual se genera una alerta de reposicion.",
    )
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["group__name", "presentation"]
        indexes = [
            models.Index(fields=["group", "is_active"], name="idx_product_group_active"),
        ]

    def __str__(self) -> str:
        detail = f" {self.presentation_detail}" if self.presentation_detail else ""
        return f"{self.group} - {self.get_presentation_display()}{detail}"

    @property
    def display_name(self) -> str:
        return str(self)

    @property
    def margin(self):
        """Margen bruto unitario estimado (precio - ultimo costo)."""
        return self.sale_price - self.last_cost


class UnitConversion(TimeStampedModel):
    """Factor de conversion entre dos presentaciones del mismo medicamento.

    Ejemplo: 1 caja -> 10 blisteres (factor 10). Se usa para registrar el
    fraccionamiento: sale una caja del inventario y entran sus blisteres.
    """

    group = models.ForeignKey(
        ProductGroup,
        on_delete=models.PROTECT,
        related_name="conversions",
        verbose_name="grupo",
    )
    source = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="conversions_from",
        verbose_name="presentacion origen",
    )
    target = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="conversions_to",
        verbose_name="presentacion destino",
    )
    factor = models.PositiveIntegerField(
        "factor",
        validators=[MinValueValidator(2)],
        help_text="Cuantas unidades del destino contiene una unidad del origen.",
    )

    class Meta:
        verbose_name = "conversion de presentacion"
        verbose_name_plural = "conversiones de presentacion"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "target"], name="unique_conversion_source_target"
            ),
            models.CheckConstraint(
                condition=models.Q(factor__gte=2), name="check_conversion_factor_gte_2"
            ),
        ]

    def __str__(self) -> str:
        return f"1 {self.source.get_presentation_display()} = {self.factor} {self.target}"

    def clean(self) -> None:
        """Valida coherencia entre grupo y presentaciones.

        No se puede expresar como restriccion de base de datos porque involucra
        dos filas de otra tabla; por eso los servicios llaman a ``full_clean()``.
        """
        super().clean()
        if self.source_id and self.target_id:
            if self.source_id == self.target_id:
                raise ValidationError("El origen y el destino deben ser presentaciones distintas.")
            if self.source.group_id != self.target.group_id:
                raise ValidationError("Las dos presentaciones deben pertenecer al mismo grupo.")
        if self.group_id and self.source_id and self.source.group_id != self.group_id:
            raise ValidationError("El grupo no coincide con el de la presentacion de origen.")
