"use strict";

/*
 * Comportamiento común de la aplicación (JavaScript vanilla):
 *  - Validación de formularios con estilos de Bootstrap (el servidor valida siempre).
 *  - Confirmación con modal para formularios con [data-confirmar].
 *  - Envío por fetch() de formularios con [data-ajax]; el servidor responde JSON.
 *  - Auto-refresco de bloques con [data-autorefresh].
 *  - Envío automático de <select data-autoenviar>.
 */
(() => {
  const CABECERAS_AJAX = { "X-Requested-With": "XMLHttpRequest" };

  function mostrarMensaje(texto, nivel = "info") {
    const contenedor = document.getElementById("mensajes-sistema");
    if (!contenedor || !texto) return;
    const alerta = document.createElement("div");
    alerta.className = `alert alert-${nivel} alert-dismissible fade show`;
    alerta.setAttribute("role", "alert");
    alerta.textContent = texto;
    const cerrar = document.createElement("button");
    cerrar.type = "button";
    cerrar.className = "btn-close";
    cerrar.dataset.bsDismiss = "alert";
    cerrar.setAttribute("aria-label", "Cerrar");
    alerta.appendChild(cerrar);
    contenedor.replaceChildren(alerta);
    if (nivel === "success" || nivel === "info") {
      setTimeout(() => bootstrap.Alert.getOrCreateInstance(alerta).close(), 4000);
    }
  }

  async function refrescarBloque(bloque) {
    try {
      const respuesta = await fetch(bloque.dataset.autorefresh, { headers: CABECERAS_AJAX });
      if (respuesta.ok) bloque.innerHTML = await respuesta.text();
    } catch (error) {
      // Sin conexión momentánea: se reintenta en el siguiente ciclo.
    }
  }

  function refrescarTodo() {
    document.querySelectorAll("[data-autorefresh]").forEach(refrescarBloque);
  }

  async function enviarAjax(form) {
    const botones = form.querySelectorAll("button[type=submit]");
    botones.forEach((b) => { b.disabled = true; });
    try {
      const respuesta = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: CABECERAS_AJAX,
        credentials: "same-origin",
      });
      const datos = await respuesta.json();
      mostrarMensaje(datos.mensaje, datos.nivel);
      document.dispatchEvent(new CustomEvent("dk:respuesta", { detail: { form, datos } }));
      if (datos.refrescar) refrescarTodo();
    } catch (error) {
      mostrarMensaje("No se pudo completar la acción. Intente de nuevo.", "danger");
    } finally {
      botones.forEach((b) => { if (b.isConnected) b.disabled = false; });
    }
  }

  function pedirConfirmacion(texto) {
    const modalEl = document.getElementById("modal-confirmacion");
    modalEl.querySelector("[data-modal-texto]").textContent = texto;
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    return new Promise((resolver) => {
      const aceptar = modalEl.querySelector("[data-modal-aceptar]");
      let aceptado = false;
      const alAceptar = () => { aceptado = true; modal.hide(); };
      aceptar.addEventListener("click", alAceptar, { once: true });
      modalEl.addEventListener("hidden.bs.modal", () => {
        aceptar.removeEventListener("click", alAceptar);
        resolver(aceptado);
      }, { once: true });
      modal.show();
    });
  }

  // Un solo manejador delegado: funciona también con HTML insertado dinámicamente.
  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    if (form.classList.contains("needs-validation") && !form.checkValidity()) {
      event.preventDefault();
      event.stopPropagation();
      form.classList.add("was-validated");
      return;
    }
    if (form.dataset.confirmar && form.dataset.confirmado !== "1") {
      event.preventDefault();
      if (await pedirConfirmacion(form.dataset.confirmar)) {
        form.dataset.confirmado = "1";
        form.requestSubmit();
      }
      return;
    }
    delete form.dataset.confirmado;
    if (form.hasAttribute("data-ajax")) {
      event.preventDefault();
      enviarAjax(form);
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target.matches("select[data-autoenviar]")) event.target.form.requestSubmit();
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".mensajes-sistema .alert-success, .mensajes-sistema .alert-info")
      .forEach((alerta) => setTimeout(() => bootstrap.Alert.getOrCreateInstance(alerta).close(), 5000));

    document.querySelectorAll("[data-autorefresh]").forEach((bloque) => {
      const segundos = Number(bloque.dataset.intervalo) || 30;
      setInterval(() => { if (!document.hidden) refrescarBloque(bloque); }, segundos * 1000);
    });
  });

  window.DarkKitchen = { mostrarMensaje, refrescarTodo };
})();
