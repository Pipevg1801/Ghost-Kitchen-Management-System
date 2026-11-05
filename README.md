# Sistema de gestión de pedidos para una cocina oculta

El proposito de esta app web es la gestión integral de pedidos en restaurantes de cocina oculta. Centraliza el ciclo completo de un pedido, desde su registro por parte del cliente hasta su despacho, garantizando la consistencia del inventario y el control de acceso por rol.

## Descripción

La aplicación da servicio a tres perfiles de usuario, cada uno con funcionalidades diferenciadas:

- **Cliente:** consulta el menú, gestiona un carrito de compra, confirma pedidos, realiza su seguimiento y puede cancelarlos mientras se encuentren en estado *Recibido*.
- **Operario:** visualiza los pedidos activos y actualiza su estado conforme al flujo *Recibido → En preparación → Listo*.
- **Administrador:** gestiona el catálogo de platos y accede a un panel de control con informes consolidados, gráficos y tabulares.

## Problema que resuelve

Las cocinas ocultas operan exclusivamente a partir de pedidos, sin atención presencial, por lo que la fiabilidad del registro de pedidos y del inventario resulta crítica. La ausencia de un sistema adecuado suele derivar en pedidos extraviados o duplicados, venta de productos sin existencias, inconsistencias en los importes y falta de información para la toma de decisiones.

El sistema aborda estas problemáticas mediante los siguientes mecanismos:

- **Consistencia del inventario:** la confirmación de cada pedido se ejecuta en una única transacción atómica con bloqueo de filas la cual valida la disponibilidad y reserva las unidades correspondientes. Ante cualquier fallo, la operación se revierte por completo.
- **Integridad de los importes:** precios, subtotales y totales se calculan exclusivamente en el servidor; los valores enviados por el cliente se descartan. Cada línea de pedido conserva el precio unitario vigente en el momento de la compra.
- **Control del flujo de trabajo:** las transiciones de estado se validan en el backend, sin permitir saltos ni retrocesos.
- **Soporte a la gestión:** los informes consolidados proporcionan visibilidad sobre la actividad del restaurante.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13, Django 5.2 |
| Base de datos | PostgreSQL 18, driver `psycopg` 3 |
| Frontend | HTML5, Bootstrap 5.3, Bootstrap Icons, JavaScript|
| Visualización de datos | Chart.js 4 |
| Autenticación | Sistema de autenticación de Django con modelo de usuario propio, inicio de sesión por correo electrónico y hashing de contraseñas PBKDF2 |

El proyecto se organiza en aplicaciones Django con responsabilidades separadas (`accounts`, `menu`, `orders`, `reports`, `core`), con vistas delgadas y la lógica de negocio encapsulada en módulos de servicios.

## Instalación (Windows)

**Requisitos previos:** Python 3.13 y PostgreSQL 18 instalados localmente.

1. Crear y activar un entorno virtual:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Crear el archivo de configuración a partir de la plantilla:

   ```bash
   copy .env.example .env
   ```

   Establecer en `.env` los valores de `SECRET_KEY` y de las variables de conexión (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`). El archivo `.env` está excluido del control de versiones y no debe publicarse.

4. Crear la base de datos:

   ```bash
   "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres restaurant_db
   ```

5. Aplicar las migraciones y, opcionalmente, cargar datos de demostración:

   ```bash
   python manage.py migrate
   python manage.py seed_data --pedidos 25
   python manage.py presentar_menu
   ```

   Las migraciones crean los roles Cliente, Operario y Administrador. El comando `seed_data` es idempotente y genera usuarios, platos y, con el parámetro `--pedidos N`, N pedidos en distintos estados. `presentar_menu` añade las categorías e imágenes ilustrativas al menú de demostración.

6. Iniciar el servidor de desarrollo:

   ```bash
   python manage.py runserver
   ```

   La aplicación queda disponible en http://127.0.0.1:8000.

7. Ejecutar la batería de pruebas (opcional):

   ```bash
   python manage.py test
   ```

   Para ello, el usuario definido en `DB_USER` debe tener permiso para crear bases de datos.

### Usuarios de prueba (solo entorno local)

| Rol | Correo electrónico | Contraseña |
|---|---|---|
| Administrador | admin@example.com | `AdminDemo#2026` |
| Operario | operario@example.com | `OperarioDemo#2026` |
| Cliente | cliente@example.com | `ClienteDemo#2026` |

## API JSON para generar informes

`GET /api/v1/informes/` devuelve el histórico completo por defecto. Con una
sesión de Administrador puedes abrirlo desde **Informes → Ver datos JSON**.
Para automatizar consultas, configura un valor aleatorio en `REPORTS_API_TOKEN`
en el entorno del servidor (o en su `.env`) y reinicia Django. El valor vacío
desactiva el acceso por token; nunca lo incluyas en el repositorio ni en la URL.
Usa HTTPS al consumir la API fuera de localhost.

Ejemplo desde PowerShell, con el mismo token disponible en el entorno del cliente:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/informes/?desde=2026-11-01&hasta=2026-11-30&por_pagina=100' -Headers @{ Authorization = "Bearer $env:REPORTS_API_TOKEN" }
```

| Parámetro | Descripción |
|---|---|
| `desde`, `hasta` | Fechas `AAAA-MM-DD`, inclusivas, en la zona horaria del restaurante. Cada límite es opcional. |
| `estado` | `RECIBIDO`, `EN_PREPARACION`, `LISTO` o `CANCELADO`. |
| `cliente` | Busca una parte del nombre o correo del cliente. |
| `pagina`, `por_pagina` | Página desde 1 y tamaño de 1 a 250. Predeterminados: 1 y 100. |

- `resumen`, `por_estado`, `serie_diaria` y `platos_mas_vendidos` cubren todo
  el resultado filtrado. Los cancelados aparecen en los conteos por estado y el
  historial, pero se excluyen de ventas, ingresos y ticket promedio. `serie_diaria`
  incluye solo los días con pedidos; el ranking incluye todos los platos con ventas.
- `pedidos` contiene una página de registros, con ID y nombre del cliente, fecha,
  estado, total y cada línea con cantidad, precio histórico y subtotal.
  Sigue `paginacion.siguiente` (ruta relativa al mismo servidor) hasta que sea
  `null`. Las páginas reflejan los datos vigentes al consultar.
- `inventario` contiene el catálogo actual completo, con categorías, precios,
  platos activos e inactivos y cantidades disponibles y reservadas. No depende
  de los filtros de pedidos; no hay un historial de movimientos de inventario.
- Los importes se entregan como cadenas decimales en COP. La API no expone
  contraseñas, correos, teléfonos, direcciones ni sesiones.

Errores JSON: `400` filtros inválidos, `401` sin autenticación, `403` rol
insuficiente, `404` página inexistente y `405` método distinto de GET.
