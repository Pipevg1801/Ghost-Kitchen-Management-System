"use strict";

// Actualiza carrito, contadores y etiquetas del menú con la respuesta del servidor.
// Los importes vienen ya calculados en el backend: aquí solo se pinta el HTML recibido.
document.addEventListener("dk:respuesta", (event) => {
  const carrito = event.detail.datos.carrito;
  if (!carrito) return;

  document.querySelectorAll("[data-carrito='compacto']").forEach((el) => {
    el.innerHTML = carrito.html_compacto;
  });
  document.querySelectorAll("[data-carrito='completo']").forEach((el) => {
    el.innerHTML = carrito.html_completo;
  });
  document.querySelectorAll(".js-carrito-contador").forEach((el) => {
    el.textContent = carrito.cantidad;
  });
  document.querySelectorAll(".js-en-carrito").forEach((el) => {
    const cantidad = carrito.por_plato[el.dataset.plato] || 0;
    el.querySelector("span").textContent = cantidad;
    el.hidden = cantidad === 0;
  });

  const form = event.detail.form;
  if (event.detail.datos.ok && form.matches("[action$='/carrito/agregar/']")) {
    const campo = form.querySelector("input[name='cantidad']");
    if (campo) campo.value = 1;
  }
});
