# Dark Kitchen: gestión de pedidos

Aplicación web para gestionar los pedidos de un restaurante de **cocina oculta (dark kitchen)**.
Los clientes consultan el menú, arman su carrito y confirman pedidos. Los operarios procesan los
pedidos activos (`Recibido → En preparación → Listo`). Los administradores gestionan el menú y
consultan informes consolidados, gráficos y tabulares.

Este prototipo se ejecuta **totalmente en local**: Django con el servidor de desarrollo y PostgreSQL instalado en el equipo.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13 + Django 5.2 |
| Base de datos | PostgreSQL (probado con la versión 18 local; driver `psycopg` 3) |
| Frontend | HTML5 + Bootstrap 5.3 + Bootstrap Icons + JavaScript vanilla |
| Gráficas | Chart.js 4 (solo en el informe gráfico) |
| Autenticación | Sistema de autenticación de Django (modelo de usuario propio, login por email) |

## Arquitectura

Proyecto Django organizado por aplicaciones con responsabilidades separadas. Las vistas son
delgadas y la lógica de negocio vive en módulos de servicios.

| App | Responsabilidad |
|---|---|
| `config` | Settings (leídos de `.env`), URLs raíz, WSGI/ASGI |
| `core` | Middleware de login obligatorio, navegación por rol, mixin Bootstrap para formularios, respuestas AJAX, filtro `moneda`, comando `seed_data` |
| `accounts` | Modelos `Rol` y `Usuario`; login, logout, registro y perfil; permisos por rol (`permissions.py`) |
| `menu` | Modelo `Plato`, catálogo para cliente y operario, gestión del menú para el administrador |
| `orders` | Modelos `Pedido` y `PedidoDetalle`, carrito en sesión (`cart.py`), reglas de negocio (`services.py`), vistas de cliente y panel del operario |
| `reports` | Dashboard e informes; consultas agregadas en `services.py` |

### Flujo de un pedido

```
Cliente: Menú → Agregar al carrito → Modificar / eliminar → Confirmar pedido
                                                              │  transaction.atomic + SELECT FOR UPDATE
                                                              ▼
                               Pedido RECIBIDO  (disponible -= n, reservada += n)
Operario:                            │  «Marcar en preparación»
                                     ▼
                               EN_PREPARACION
                                     │  «Marcar listo»
                                     ▼
                               LISTO            (reservada -= n: el plato se consumió)

Cliente (solo si está RECIBIDO): Cancelar → CANCELADO (disponible += n, reservada -= n)
```

- El carrito se guarda en la sesión como `{id_plato: cantidad}`. **Precios, subtotales y totales se
  calculan siempre en el servidor**; lo que envíe el navegador se ignora.
- La confirmación valida la disponibilidad de todos los productos, bloquea las filas de `platos` y
  crea el pedido y sus detalles en una única transacción. Si algo falla, no queda nada a medias.
- Las transiciones de estado se validan en el backend (`Pedido.TRANSICIONES`). No se permiten
  saltos ni retrocesos.

### Modelo de datos

Correspondencia directa con el diseño (se conservan los nombres de tablas y columnas):

```
roles(id_rol, nombre)
  1 ─── N
usuarios(id_usuario, id_rol, nombre, email UNIQUE, fecha_creacion, activo, telefono, direccion, password)
  1 ─── N
pedidos(id_movimiento, id_usuario, fecha_creacion, estado, total)
  1 ─── N
pedidos_detalles(id_detalle, id_plato, id_movimiento, cantidad, precio_unitario)
  N ─── 1
platos(id_plato, nombre, precio, descripcion, cantidad_disponible, cantidad_reservada)
```

| Tabla | Modelo Django | Notas |
|---|---|---|
| `roles` | `accounts.Rol` | Cliente, Operario y Administrador (creados por migración) |
| `usuarios` | `accounts.Usuario` | `AUTH_USER_MODEL`; password con hashing PBKDF2 de Django |
| `platos` | `menu.Plato` | `precio` es `DecimalField`. Campo extra `activo`: un plato con pedidos se oculta en lugar de borrarse |
| `pedidos` | `orders.Pedido` | `estado` con `TextChoices`: `RECIBIDO`, `EN_PREPARACION`, `LISTO`, `CANCELADO` |
| `pedidos_detalles` | `orders.PedidoDetalle` | Guarda el `precio_unitario` histórico |

Restricciones en la base de datos: precio > 0, cantidades ≥ 0, cantidad de detalle > 0, total ≥ 0,
estado válido, un plato una sola vez por pedido y email único. Hay índices por estado/fecha,
usuario/fecha y plato activo/nombre.

### Seguridad y roles

- `LoginRequeridoMiddleware`: **toda** URL exige sesión, salvo login y registro.
- Cada vista declara su rol con decoradores (`cliente_requerido`, `operario_requerido`,
  `administrador_requerido`) o mixins. Si un usuario entra por URL a una función de otro rol, recibe
  **HTTP 403**. No se confía en ocultar botones.
- Un cliente solo ve y cancela **sus** pedidos: los ajenos devuelven 404.
- CSRF en todos los formularios y en las peticiones `fetch()`, logout por POST, validación
  en frontend (HTML5 + Bootstrap) y en backend (Django Forms + restricciones de BD).

| Funcionalidad | Cliente | Operario | Administrador |
|---|:-:|:-:|:-:|
| Menú (consulta) | ✔ | ✔ | (usa Gestión del menú) |
| Carrito, confirmar y cancelar pedidos | ✔ | ✖ | ✖ |
| Mis pedidos / seguimiento | ✔ | ✖ | ✖ |
| Pedidos activos y cambio de estado | ✖ | ✔ | ✖ |
| Detalle de pedido | propios | ✔ | ✔ |
| Gestión del menú | ✖ | ✖ | ✔ |
| Dashboard e informes | ✖ | ✖ | ✔ |

## URLs principales

| Ruta | Descripción |
|---|---|
| `/login/`, `/logout/`, `/registro/`, `/perfil/` | Autenticación y perfil |
| `/menu/` | Menú (cliente: con carrito lateral; operario: consulta) |
| `/carrito/`, `/carrito/agregar/`, `/carrito/modificar/`, `/carrito/eliminar/`, `/carrito/cancelar/` | Carrito |
| `/pedido/confirmar/` | Confirmar pedido |
| `/pedidos/`, `/pedidos/<id>/`, `/pedidos/<id>/cancelar/` | Pedidos del cliente |
| `/operario/pedidos/`, `/operario/pedidos/<id>/estado/` | Panel del operario |
| `/admin-panel/` | Dashboard administrativo |
| `/admin-panel/menu/`, `/admin-panel/menu/agregar/`, `/admin-panel/menu/<id>/editar/`, `/admin-panel/menu/<id>/eliminar/` | Gestión del menú |
| `/informes/`, `/informes/consolidado/`, `/informes/grafico/`, `/informes/tabular/` | Informes |
| `/django-admin/` | Admin de Django (solo administradores) |

## Estructura de carpetas

```
Ingenieria_Software_2/
├── manage.py
├── config/            settings.py, urls.py, wsgi.py, asgi.py
├── core/              middleware.py, navegacion.py, context_processors.py, forms.py, http.py,
│                      templatetags/formato.py, management/commands/seed_data.py, tests_utils.py
├── accounts/          models.py, managers.py, permissions.py, forms.py, views.py, urls.py, admin.py, tests.py
├── menu/              models.py, forms.py, views.py, urls.py, admin.py, tests.py
├── orders/            models.py, cart.py, services.py, forms.py, views.py, urls.py,
│                      context_processors.py, templatetags/pedidos.py, tests.py, tests_views.py
├── reports/           services.py, forms.py, views.py, urls.py, tests.py
├── templates/         base.html, 403.html, 404.html, includes/, accounts/, menu/, orders/, reports/
├── static/            css/app.css, js/app.js, js/carrito.js, js/informes.js
├── requirements.txt
├── .env.example
└── README.md
```

## Instalación (Windows)

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```
```bash
copy .env.example .env
```

## Configuración de PostgreSQL

1. Cree la base de datos con el usuario `postgres` de su instalación local:

   ```bash
   "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres restaurant_db
   ```

2. Edite `.env` y coloque la contraseña de su usuario de PostgreSQL en `DB_PASSWORD`.

Para ejecutar los tests, el usuario de `DB_USER` necesita permiso para crear bases de datos
(el usuario `postgres` lo tiene).

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL |
| `SECRET_KEY` | Clave secreta de Django (obligatoria) |
| `DEBUG` | `True` en desarrollo |
| `ALLOWED_HOSTS` | Hosts separados por coma |

El archivo `.env` real está en `.gitignore` y nunca debe subirse al repositorio.

## Migraciones

```bash
python manage.py migrate
```

La migración `accounts/0002_roles_iniciales` crea los roles Cliente, Operario y Administrador.

## Seed de datos

```bash
python manage.py seed_data --pedidos 25
```

Es idempotente para roles, usuarios y platos. `--pedidos N` genera además N pedidos de
demostración en distintos estados y repartidos en los últimos 14 días. Se crean con los mismos
servicios que la aplicación, así que el inventario queda consistente, y sirven para evaluar el
panel del operario y los informes. Si no pasa `--pedidos`, no se crean pedidos.

## Creación de superusuario

```bash
python manage.py createsuperuser
```

El superusuario recibe el rol Administrador.

## Ejecución del servidor

```bash
python manage.py runserver
```

Abra http://127.0.0.1:8000 e inicie sesión con alguno de los usuarios de prueba.

## Ejecución de tests

```bash
python manage.py test
```

Hay 110 pruebas que cubren autenticación, roles y permisos, menú, carrito, pedidos, transiciones de estado,
inventario e informes.

## Usuarios de prueba (solo entorno local)

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | admin@example.com | `AdminDemo#2026` |
| Operario | operario@example.com | `OperarioDemo#2026` |
| Cliente | cliente@example.com | `ClienteDemo#2026` |
| Cliente | cliente2@example.com | `ClienteDemo#2026` |
