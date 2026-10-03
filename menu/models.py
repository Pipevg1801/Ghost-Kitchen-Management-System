from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class PlatoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def con_disponibilidad(self):
        return self.activos().filter(cantidad_disponible__gt=0)


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
        ]

    def __str__(self):
        return self.nombre

    @property
    def agotado(self):
        return self.cantidad_disponible == 0
