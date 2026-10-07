from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class CategoriaQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(activa=True)


class Categoria(models.Model):
    """Categoría del menú: bebidas, entradas, plato fuerte, postres, etc."""

    id = models.BigAutoField(primary_key=True, db_column="id_categoria")
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    activa = models.BooleanField(default=True)

    objects = CategoriaQuerySet.as_manager()

    class Meta:
        db_table = "categorias"
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["orden", "nombre"]
        indexes = [
            models.Index(fields=["activa", "orden"], name="categorias_activa_orden_idx"),
        ]

    def __str__(self):
        return self.nombre


class PlatoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def con_disponibilidad(self):
        return self.activos().filter(cantidad_disponible__gt=0)

    # 👇 NUEVO: helper para filtrar por categoría
    def de_categoria(self, slug):
        return self.filter(categoria__slug=slug, categoria__activa=True)


class Plato(models.Model):
    """Tabla `platos`. Plato 1 ─── N PedidoDetalle."""

    id = models.BigAutoField(primary_key=True, db_column="id_plato")
    nombre = models.CharField(max_length=120, unique=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"), "El precio debe ser mayor que cero.")],
    )
    descripcion = models.TextField("descripción", blank=True)
    cantidad_disponible = models.PositiveIntegerField(default=0)
    cantidad_reservada = models.PositiveIntegerField(default=0)
    # Un plato con pedidos históricos no se borra físicamente: se desactiva
    # para conservar la integridad de los detalles de pedido.
    activo = models.BooleanField(default=True)

    # 👇 NUEVO: categoría y imagen (no rompen nada existente)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="platos",
        null=True,          # temporal para no romper filas existentes
        blank=True,
        db_column="id_categoria",
    )
    imagen = models.ImageField(
        upload_to="platos/",
        blank=True,
        null=True,
        help_text="Imagen del plato (JPG o PNG, máx 2 MB recomendado).",
    )

    objects = PlatoQuerySet.as_manager()

    class Meta:
        db_table = "platos"
        verbose_name = "plato"
        verbose_name_plural = "platos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(precio__gt=0), name="platos_precio_positivo"),
            models.CheckConstraint(
                condition=Q(cantidad_disponible__gte=0), name="platos_disponible_no_negativa"
            ),
            models.CheckConstraint(
                condition=Q(cantidad_reservada__gte=0), name="platos_reservada_no_negativa"
            ),
        ]
        indexes = [
            models.Index(fields=["activo", "nombre"], name="platos_activo_nombre_idx"),
            # 👇 NUEVO: índice para filtrar por categoría (opcional pero útil)
            models.Index(fields=["categoria", "activo"], name="platos_categoria_activo_idx"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def agotado(self):
        return self.cantidad_disponible == 0
