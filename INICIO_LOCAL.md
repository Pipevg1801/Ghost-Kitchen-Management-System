# Ejecución local

Repositorio original: https://github.com/Pipevg1801/Ghost-Kitchen-Management-System

La rama `juan` parte de `feature/categorias-e-imagenes` y contiene el rediseño
del restaurante y la API de informes. Las migraciones de categorías e imágenes
se aplicaron a la base local.

Python está aislado en `.venv`. PostgreSQL 18.6 se ejecuta desde `.runtime/pgsql`,
en el puerto local 55432, con datos persistentes en `.runtime/pgdata`.
La configuración y las claves locales están en `.env` (excluido de Git).

## Iniciar de nuevo

Ejecuta PowerShell en esta carpeta (no requiere Docker):

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar-local.ps1
```

Accede a http://127.0.0.1:8000. Sin iniciar sesión se abre la página pública del
restaurante; puedes explorar el menú y entrar al elegir un plato. También está
disponible directamente en http://127.0.0.1:8000/restaurante/.

## Cuentas de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@example.com | AdminDemo#2026 |
| Operario | operario@example.com | OperarioDemo#2026 |
| Cliente | cliente@example.com | ClienteDemo#2026 |

## Datos para informes

Con una sesión de Administrador, abre **Informes → Ver datos JSON** o entra en
http://127.0.0.1:8000/api/v1/informes/. Los filtros, la paginación y el acceso
opcional por token están descritos en [API JSON para generar informes](README.md#api-json-para-generar-informes).

## Detener

Si iniciaste el servidor con el script, pulsa Ctrl+C en su terminal.
La ejecución actual se dejó en segundo plano: su PID está en `.runtime/django.pid`
y sus logs en `.runtime/informes.stdout.log` y `.runtime/informes.stderr.log`.
Para detener la base de datos conservando los datos:

```powershell
.\.runtime\pgsql\bin\pg_ctl.exe -D .runtime\pgdata -m fast -w stop
```

## Comprobar

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Es una ejecución local con el servidor de desarrollo de Django.
Se cargaron cuatro usuarios de prueba, cinco platos y 25 pedidos de demostración.
La instalación activa usa PostgreSQL local; Docker Desktop presentó errores de acceso
a sus sockets durante el arranque.

## Frontend

Las preferencias de movimiento son Automático, Completo y Reducido y se guardan
en este navegador. Automático respeta la preferencia de accesibilidad del sistema.
La interfaz usa verdes y blancos, con navegación horizontal, portada culinaria,
categorías, búsqueda y un carrito lateral que se abre al pedir. Las pantallas de
administración conservan sus funciones y usan la misma paleta.

Los cinco platos de demostración tienen nombre y fotografías ilustrativas propias:
Burger de la casa, Parrillada para compartir, Bowl teriyaki, Pasta al pesto y
Limonada de coco. Sus precios, existencias y pedidos se conservaron. El catálogo
también conserva las fotografías subidas desde la administración.

Para aplicar las imágenes y nombres a los platos de demostración de otra base local:

```powershell
.\.venv\Scripts\python.exe manage.py presentar_menu
```

El comando es idempotente y respeta las imágenes personalizadas ya cargadas.

Referencias de composición revisadas: [McDonald's Colombia](https://www.mcdonalds.com.co/),
[Subway Colombia](https://www.subway.com/es-co) y [El Corral](https://www.elcorral.com/).
Se tomaron como referencia la comida protagonista, el acceso al pedido y las categorías.
La identidad, textos y recursos del proyecto son propios.

Las cinco fotografías de `static/img/food/` se crearon con la herramienta integrada
de imagegen y se optimizaron a WebP. Se muestran como imágenes ilustrativas.
Los prompts completos y la procedencia están en `static/img/food/README.md`.

## Validación del rediseño

- `manage.py check`: sin incidencias. `manage.py test --noinput`: 124 pruebas pasadas,
  incluidas las de acceso y datos de la API.
- Restaurante público y catálogo revisados a 320, 390, 768, 1024 y 1440 px sin desbordamiento.
- Cinco imágenes cargadas, categorías y búsqueda comprobadas con datos reales del servidor.
- Carrito: agregar, incrementar, disminuir y vaciar mediante la respuesta real del servidor.
- Movimiento: seguimiento continuo del cursor, presión, liberación fuera, vuelta al reposo,
  limpieza de ondas, salida y entrada superpuestas, y transición entre páginas.
- Preferencias: Automático respeta el sistema; Experiencia viva prevalece cuando se elige
  explícitamente; Movimiento reducido elimina los efectos. La elección persiste al recargar.
- Teclado y móvil emulado: cierre del diálogo con Space, navegación con Escape y cancelación
  de presión al comenzar el scroll táctil. No se probó un teléfono físico.

Capturas del diseño verde y blanco: `output/playwright/restaurante-verde-desktop.png`,
`restaurante-verde-portada.png` y `restaurante-verde-mobile.png`.
