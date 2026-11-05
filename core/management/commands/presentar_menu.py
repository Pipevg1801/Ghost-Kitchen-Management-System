"""Da nombres, categorías e imágenes a los cinco platos de demostración."""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from menu.models import Categoria, Plato

PRESENTACION = (
    ("Ítem del menú #1", "Burger de la casa", "Hamburguesas", "hamburguesas", "burger"),
    ("Ítem del menú #2", "Parrillada para compartir", "Parrilla", "parrilla", "grill"),
    ("Ítem del menú #3", "Bowl teriyaki", "Bowls", "bowls", "bowl"),
    ("Ítem del menú #4", "Pasta al pesto", "Pastas", "pastas", "pasta"),
    ("Ítem del menú #5", "Limonada de coco", "Bebidas", "bebidas", "lemonade"),
)


class Command(BaseCommand):
    help = "Presenta los platos demo sin modificar sus precios, existencias ni pedidos."

    @transaction.atomic
    def handle(self, *args, **options):
        for orden, (anterior, nombre, categoria, slug, imagen) in enumerate(PRESENTACION, 1):
            plato = Plato.objects.filter(nombre__in=(anterior, nombre)).order_by("id").first()
            if plato is None:
                continue
            cambios = []
            if plato.nombre == anterior:
                plato.nombre = nombre
                cambios.append("nombre")
            if not plato.categoria_id:
                plato.categoria, _ = Categoria.objects.get_or_create(
                    slug=slug, defaults={"nombre": categoria, "orden": orden}
                )
                cambios.append("categoria")
            source = settings.BASE_DIR / "static" / "img" / "food" / f"{imagen}.webp"
            # Una fotografía subida desde administración tiene prioridad sobre el ejemplo.
            if source.exists() and (not plato.imagen or plato.imagen.name.startswith("platos/demo/")):
                nombre_archivo = f"platos/demo/{imagen}.webp"
                destino = Path(settings.MEDIA_ROOT) / nombre_archivo
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destino)
                plato.imagen = nombre_archivo
                cambios.append("imagen")
            if cambios:
                plato.save(update_fields=cambios)
            self.stdout.write(nombre)
