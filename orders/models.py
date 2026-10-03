from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce

from menu.models import Plato


class EstadoPedido(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    EN_PREPARACION = "EN_PREPARACION", "En preparación"
    LISTO = "LISTO", "Listo"
    CANCELADO = "CANCELADO", "Cancelado"


class PedidoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(estado__in=Pedido.ESTADOS_ACTIVOS)

    def del_usuario(self, usuario):
        return self.filter(usuario=usuario)

    def no_cancelados(self):
        return self.exclude(estado=Pedido.Estado.CANCELADO)

    def con_detalles(self):
        return self.select_related("usuario").prefetch_related("detalles__plato")


class Pedido(models.Model):
    """Tabla `pedidos`. Usuario 1 ─── N Pedidos; Pedido 1 ─── N PedidoDetalle."""

    Estado = EstadoPedido

    # Única transición permitida desde cada estado (flujo del diseño).
    TRANSICIONES = {
        Estado.RECIBIDO: Estado.EN_PREPARACION,
        Estado.EN_PREPARACION: Estado.LISTO,
    }
    ESTADOS_ACTIVOS = (Estado.RECIBIDO, Estado.EN_PREPARACION)
    ESTADOS_CANCELABLES = (Estado.RECIBIDO,)

    id = models.BigAutoField(primary_key=True, db_column="id_movimiento")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
        db_column="id_usuario",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.RECIBIDO
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    objects = PedidoQuerySet.as_manager()

    class Meta:
        db_table = "pedidos"
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gte=0), name="pedidos_total_no_negativo"),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoPedido.values),
                name="pedidos_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["estado", "fecha_creacion"], name="pedidos_estado_fecha_idx"),
            models.Index(fields=["usuario", "fecha_creacion"], name="pedidos_usuario_fecha_idx"),
        ]

    def __str__(self):
        return f"Pedido #{self.pk}"

    @property
    def siguiente_estado(self):
        return self.TRANSICIONES.get(self.estado)

    @property
    def siguiente_estado_label(self):
        siguiente = self.siguiente_estado
        return self.Estado(siguiente).label if siguiente else None

    def puede_transicionar_a(self, nuevo_estado):
        return nuevo_estado is not None and self.siguiente_estado == nuevo_estado

    @property
    def esta_activo(self):
        return self.estado in self.ESTADOS_ACTIVOS

    @property
    def puede_cancelarse(self):
        return self.estado in self.ESTADOS_CANCELABLES

    def calcular_total(self):
        """Suma de cantidad × precio_unitario de los detalles, calculada en PostgreSQL."""
        subtotal = ExpressionWrapper(
            F("cantidad") * F("precio_unitario"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        return self.detalles.aggregate(
            total=Coalesce(Sum(subtotal), Decimal("0.00"),
                           output_field=DecimalField(max_digits=12, decimal_places=2))
        )["total"]


class PedidoDetalle(models.Model):
    """Tabla `pedidos_detalles`. Guarda el precio histórico de cada plato."""

    id = models.BigAutoField(primary_key=True, db_column="id_detalle")
    plato = models.ForeignKey(
        Plato,
        on_delete=models.PROTECT,
        related_name="detalles",
        db_column="id_plato",
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
        db_column="id_movimiento",
    )
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        db_table = "pedidos_detalles"
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["pedido", "plato"], name="detalle_plato_unico_por_pedido"),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="detalle_cantidad_positiva"),
            models.CheckConstraint(
                condition=Q(precio_unitario__gt=0), name="detalle_precio_positivo"
            ),
        ]

    def __str__(self):
        return f"{self.plato} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
