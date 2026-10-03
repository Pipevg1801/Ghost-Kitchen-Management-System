"use strict";

// Informe gráfico: obtiene los datos reales desde /informes/grafico/datos/ y
// los dibuja con Chart.js. Se refresca al cambiar el rango y cada 60 s.
(() => {
  const contenedor = document.querySelector("[data-grafico-url]");
  if (!contenedor || typeof Chart === "undefined") return;

  const estilos = getComputedStyle(document.documentElement);
  const color = (variable) => estilos.getPropertyValue(variable).trim();
  const COLORES = {
    RECIBIDO: color("--estado-recibido"),
    EN_PREPARACION: color("--estado-en-preparacion"),
    LISTO: color("--estado-listo"),
    CANCELADO: color("--estado-cancelado"),
  };
  const TINTA = color("--grafico-tinta");
  const REJILLA = color("--grafico-rejilla");
  const SUPERFICIE = color("--grafico-superficie");
  const moneda = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = TINTA;

  const ejes = (formatoY) => ({
    x: { stacked: true, grid: { display: false }, border: { color: REJILLA } },
    y: {
      stacked: true, beginAtZero: true, border: { display: false },
      grid: { color: REJILLA }, ticks: { precision: 0, callback: formatoY },
    },
  });
  const opcionesBase = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { display: false } },
  };

  const lienzo = (nombre) => contenedor.querySelector(`[data-grafico='${nombre}']`);
  const estadoTexto = contenedor.querySelector("[data-grafico-estado]");
  const selectorDias = contenedor.querySelector("[data-grafico-dias]");

  const graficoDiario = new Chart(lienzo("diario"), {
    type: "bar",
    data: { labels: [], datasets: [] },
    options: { ...opcionesBase, scales: ejes() },
  });
  const graficoEstados = new Chart(lienzo("estados"), {
    type: "bar",
    data: { labels: [], datasets: [] },
    options: {
      ...opcionesBase,
      indexAxis: "y",
      interaction: { mode: "nearest", intersect: true },
      scales: {
        x: { beginAtZero: true, grid: { color: REJILLA }, border: { display: false }, ticks: { precision: 0 } },
        y: { grid: { display: false } },
      },
    },
  });
  const graficoIngresos = new Chart(lienzo("ingresos"), {
    type: "line",
    data: { labels: [], datasets: [] },
    options: {
      ...opcionesBase,
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true, grid: { color: REJILLA }, border: { display: false },
          ticks: { callback: (valor) => moneda.format(valor) },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` Ingresos: ${moneda.format(ctx.parsed.y)}` } },
      },
    },
  });

  function pintar(datos) {
    graficoDiario.data.labels = datos.etiquetas;
    graficoDiario.data.datasets = datos.series.map((serie) => ({
      label: serie.etiqueta,
      data: serie.datos,
      backgroundColor: COLORES[serie.estado],
      borderColor: SUPERFICIE,
      borderWidth: { top: 2 },
      borderRadius: 4,
      borderSkipped: "bottom",
      maxBarThickness: 32,
    }));
    graficoDiario.update();

    graficoEstados.data.labels = datos.series.map((serie) => serie.etiqueta);
    graficoEstados.data.datasets = [{
      label: "Pedidos",
      data: datos.series.map((serie) => datos.totales_por_estado[serie.estado]),
      backgroundColor: datos.series.map((serie) => COLORES[serie.estado]),
      borderRadius: 4,
      maxBarThickness: 28,
    }];
    graficoEstados.update();

    graficoIngresos.data.labels = datos.etiquetas;
    graficoIngresos.data.datasets = [{
      label: "Ingresos",
      data: datos.ingresos,
      borderColor: color("--grafico-ingresos"),
      backgroundColor: color("--grafico-ingresos"),
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBorderColor: SUPERFICIE,
      pointBorderWidth: 2,
      tension: 0,
    }];
    graficoIngresos.update();

    const total = Object.values(datos.totales_por_estado).reduce((a, b) => a + b, 0);
    estadoTexto.textContent = `${total} pedidos en los últimos ${datos.dias} días · actualizado ${new Date().toLocaleTimeString("es-CO")}`;
  }

  async function cargar() {
    const url = new URL(contenedor.dataset.graficoUrl, window.location.origin);
    url.searchParams.set("dias", selectorDias.value);
    try {
      const respuesta = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!respuesta.ok) throw new Error(respuesta.statusText);
      pintar(await respuesta.json());
    } catch (error) {
      estadoTexto.textContent = "No se pudieron cargar los datos del gráfico.";
    }
  }

  selectorDias.addEventListener("change", cargar);
  setInterval(() => { if (!document.hidden) cargar(); }, 60000);
  cargar();
})();
