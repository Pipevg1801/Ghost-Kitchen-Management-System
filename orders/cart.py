"""Carrito de compras almacenado en la sesión de Django.

Solo guarda {id_plato: cantidad}. Precios y disponibilidad se leen siempre de
la base de datos, nunca del navegador.
"""
from dataclasses import dataclass
from decimal import Decimal

from menu.models import Plato

CLAVE_SESION = "carrito"


class ErrorCarrito(Exception):
    pass


@dataclass(frozen=True)
class ItemCarrito:
    plato: Plato
    cantidad: int

    @property
    def precio_unitario(self):
        return self.plato.precio

    @property
    def subtotal(self):
        return self.plato.precio * self.cantidad

    @property
    def puede_incrementar(self):
        return self.cantidad < self.plato.cantidad_disponible

    @property
    def supera_disponibilidad(self):
        return self.cantidad > self.plato.cantidad_disponible


class Carrito:
    def __init__(self, request):
        self.session = request.session
        datos = self.session.get(CLAVE_SESION, {})
        self._items = {}
        for plato_id, cantidad in datos.items():
            try:
                plato_id, cantidad = int(plato_id), int(cantidad)
            except (TypeError, ValueError):
                continue
            if cantidad > 0:
                self._items[str(plato_id)] = cantidad

    def __len__(self):
        return sum(self._items.values())

    @property
    def esta_vacio(self):
        return not self._items

    def cantidad_de(self, plato):
        return self._items.get(str(plato.pk), 0)

    def cantidades(self):
        return {int(plato_id): cantidad for plato_id, cantidad in self._items.items()}

    def agregar(self, plato, cantidad=1):
        if cantidad < 1:
            raise ErrorCarrito("La cantidad debe ser mayor que cero.")
        if not plato.activo:
            raise ErrorCarrito("Este producto ya no está disponible en el menú.")
        nueva_cantidad = self.cantidad_de(plato) + cantidad
        if nueva_cantidad > plato.cantidad_disponible:
            raise ErrorCarrito(
                f"No hay suficiente disponibilidad de {plato.nombre} "
                f"(disponibles: {plato.cantidad_disponible})."
            )
        self._items[str(plato.pk)] = nueva_cantidad
        self._guardar()

    def incrementar(self, plato):
        self.agregar(plato, 1)

    def disminuir(self, plato):
        nueva_cantidad = self.cantidad_de(plato) - 1
        if nueva_cantidad <= 0:
            self.eliminar(plato)
        else:
            self._items[str(plato.pk)] = nueva_cantidad
            self._guardar()

    def eliminar(self, plato):
        if self._items.pop(str(plato.pk), None) is not None:
            self._guardar()

    def vaciar(self):
        self._items = {}
        self._guardar()

    def items(self):
        """Ítems con datos actuales de la BD; descarta platos desactivados o borrados."""
        if not self._items:
            return []
        platos = Plato.objects.activos().in_bulk([int(pk) for pk in self._items])
        descartados = [pk for pk in self._items if int(pk) not in platos]
        if descartados:
            for pk in descartados:
                del self._items[pk]
            self._guardar()
        items = [ItemCarrito(platos[int(pk)], cantidad) for pk, cantidad in self._items.items()]
        return sorted(items, key=lambda item: item.plato.nombre)

    def resumen(self):
        items = self.items()
        return {
            "items": items,
            "cantidad": sum(item.cantidad for item in items),
            "total": sum((item.subtotal for item in items), Decimal("0.00")),
            "hay_faltantes": any(item.supera_disponibilidad for item in items),
        }

    def _guardar(self):
        self.session[CLAVE_SESION] = dict(self._items)
        self.session.modified = True
