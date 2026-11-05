"use strict";

/* Esmooth: el gesto cambia el objetivo; una sola interpolación conserva la pose
 * visible al entrar, salir o interrumpir. El ticker se apaga al estabilizarse. */
(() => {
  const controls = ".btn:not(:disabled), .sidebar-link, .restaurant-nav-link, .nav-pills .nav-link, .category-link";
  const cards = ".tarjeta-plato, .tarjeta-kpi, .acceso-rapido, .tarjeta-pedido, [data-motion-card]";
  const selector = `${controls}, ${cards}`;
  const fine = matchMedia("(hover: hover) and (pointer: fine)");
  const surfaces = new Map();
  const waves = new Map();
  const animations = new Set();
  const outgoing = new Set();
  const rest = () => ({ x: 0, y: 0, rx: 0, ry: 0, scale: 1, glow: 0 });
  let frame = 0;
  let previousTime = 0;
  let replacementSerial = 0;
  const blockSignatures = new WeakMap();

  function enabled() { return window.KitchenMotion?.enabled && !document.hidden; }
  function obtain(node) {
    if (!surfaces.has(node)) {
      surfaces.set(node, { node, value: rest(), target: rest(), hover: false, focused: false, pressed: false, card: node.matches(cards) });
      node.dataset.reactive = "true";
    }
    return surfaces.get(node);
  }
  function affected(target) {
    const nodes = [];
    let node = target instanceof Element ? target.closest(selector) : null;
    while (node) {
      nodes.push(node);
      node = node.parentElement?.closest(cards);
    }
    return nodes;
  }
  function paint(item) {
    const v = item.value;
    item.node.style.transform = `perspective(900px) translate3d(${v.x}px, ${v.y}px, 0) rotateX(${v.rx}deg) rotateY(${v.ry}deg) scale(${v.scale})`;
    item.node.style.setProperty("--engaged", v.glow);
  }
  function tick(time) {
    const dt = Math.min((time - (previousTime || time - 16)) / 1000, .032);
    previousTime = time;
    const amount = 1 - Math.exp(-18 * dt);
    let moving = false;
    surfaces.forEach((item, node) => {
      if (!node.isConnected) { surfaces.delete(node); return; }
      let error = 0;
      for (const key of Object.keys(item.value)) {
        item.value[key] += (item.target[key] - item.value[key]) * amount;
        error = Math.max(error, Math.abs(item.target[key] - item.value[key]));
      }
      if (error > .0008) { moving = true; node.style.willChange = "transform"; }
      else { item.value = { ...item.target }; node.style.removeProperty("will-change"); }
      paint(item);
    });
    frame = moving && enabled() ? requestAnimationFrame(tick) : 0;
    if (!frame) previousTime = 0;
  }
  function wake() { if (!frame && enabled()) frame = requestAnimationFrame(tick); }
  function aim(item) {
    if (item.pressed) item.target = { ...rest(), y: 1, scale: item.card ? .985 : .945, glow: 1 };
    else if (item.hover || item.focused) item.target = { ...item.target, y: item.card ? -3 : -1.5, scale: item.card ? 1.012 : 1.025, glow: 1 };
    else item.target = rest();
    wake();
  }
  function clearWave(wave) { clearTimeout(waves.get(wave)); waves.delete(wave); wave.remove(); }
  function ripple(node, x, y) {
    if (!node.matches(controls)) return;
    node.querySelectorAll(".touch-ripple").forEach(clearWave);
    const rect = node.getBoundingClientRect();
    const wave = document.createElement("span");
    wave.className = "touch-ripple";
    wave.setAttribute("aria-hidden", "true");
    wave.style.setProperty("--ripple-x", `${x ?? rect.width / 2}px`);
    wave.style.setProperty("--ripple-y", `${y ?? rect.height / 2}px`);
    wave.style.setProperty("--ripple-size", `${Math.max(rect.width, rect.height) * 2}px`);
    node.append(wave);
    waves.set(wave, setTimeout(() => clearWave(wave), 750));
    wave.addEventListener("animationend", () => clearWave(wave), { once: true });
  }
  function release() {
    surfaces.forEach(item => {
      if (!item.pressed) return;
      item.pressed = false;
      if (!fine.matches) item.hover = false;
      aim(item);
    });
  }
  function reset() {
    cancelAnimationFrame(frame); frame = 0; previousTime = 0;
    surfaces.forEach(({ node }) => {
      node.style.removeProperty("transform");
      node.style.removeProperty("will-change");
      node.style.removeProperty("--engaged");
      delete node.dataset.reactive;
    });
    surfaces.clear();
    Array.from(waves.keys()).forEach(clearWave);
    animations.forEach(animation => animation.cancel());
    animations.clear();
    outgoing.forEach(node => node.remove());
    outgoing.clear();
  }
  function animate(node, keyframes, options) {
    if (!enabled() || !node.animate) return;
    const animation = node.animate(keyframes, options);
    animations.add(animation);
    animation.finished.catch(() => {}).finally(() => animations.delete(animation));
    return animation;
  }

  document.addEventListener("pointerover", event => {
    if (!enabled() || !fine.matches || event.pointerType === "touch") return;
    affected(event.target).forEach(node => {
      if (event.relatedTarget instanceof Node && node.contains(event.relatedTarget)) return;
      const item = obtain(node); item.hover = true; aim(item);
    });
  });
  document.addEventListener("pointerout", event => {
    affected(event.target).forEach(node => {
      if (event.relatedTarget instanceof Node && node.contains(event.relatedTarget)) return;
      const item = surfaces.get(node);
      if (item) { item.hover = false; item.pressed = false; aim(item); }
    });
  });
  document.addEventListener("pointermove", event => {
    if (!enabled() || !fine.matches || event.pointerType === "touch") return;
    // Leer toda la geometría antes de escribir para evitar recalcular el layout por superficie.
    const reads = affected(event.target).map(node => ({ node, rect: node.getBoundingClientRect() }));
    reads.forEach(({ node, rect }) => {
      const item = obtain(node);
      const u = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
      const v = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
      node.style.setProperty("--pointer-x", `${(u + 1) * 50}%`);
      node.style.setProperty("--pointer-y", `${(v + 1) * 50}%`);
      if (!item.pressed) { item.target.x = u * (item.card ? 1.2 : .5); item.target.rx = item.card ? -v * 1.5 : 0; item.target.ry = item.card ? u * 2 : 0; wake(); }
    });
  });
  document.addEventListener("pointerdown", event => {
    if (!enabled() || event.button !== 0) return;
    affected(event.target).forEach(node => {
      const item = obtain(node); item.pressed = true; aim(item);
      const rect = node.getBoundingClientRect(); ripple(node, event.clientX - rect.left, event.clientY - rect.top);
    });
  });
  document.addEventListener("focusin", event => {
    if (!enabled()) return;
    affected(event.target).forEach(node => {
      const item = obtain(node); item.focused = event.target.matches(":focus-visible"); aim(item);
    });
  });
  document.addEventListener("focusout", event => {
    affected(event.target).forEach(node => {
      if (event.relatedTarget instanceof Node && node.contains(event.relatedTarget)) return;
      const item = surfaces.get(node);
      if (item) { item.focused = false; item.pressed = false; aim(item); }
    });
  });
  document.addEventListener("keydown", event => {
    if (!enabled() || event.repeat || !["Enter", " "].includes(event.key)) return;
    const node = event.target instanceof Element ? event.target.closest(controls) : null;
    if (!node || (event.key === " " && !node.matches("button"))) return;
    const item = obtain(node); item.pressed = true; aim(item); ripple(node);
  });
  window.addEventListener("keyup", release);
  window.addEventListener("pointerup", release);
  window.addEventListener("pointercancel", release);
  window.addEventListener("blur", () => reset());
  window.addEventListener("pagehide", reset);
  document.addEventListener("visibilitychange", () => { if (document.hidden) reset(); });
  document.addEventListener("hidden.bs.modal", () => { release(); Array.from(waves.keys()).forEach(clearWave); });
  document.addEventListener("hidden.bs.offcanvas", () => { release(); Array.from(waves.keys()).forEach(clearWave); });
  document.addEventListener("change", event => {
    if (event.target.matches("[data-motion-select]")) window.KitchenMotion.setChoice(event.target.value);
  });
  function syncPreference() {
    if (!enabled()) reset();
    document.querySelectorAll("[data-motion-select]").forEach(select => { select.value = window.KitchenMotion.choice; });
  }
  document.addEventListener("dk:motion", syncPreference);
  syncPreference();

  // El contenido nuevo se inserta inmediatamente. Sólo la copia visual de salida
  // permanece superpuesta durante 320 ms, inerte y sin identificadores duplicados.
  function replace(node, html) {
    // Un token CSRF enmascarado distinto no significa que el pedido haya cambiado.
    const signature = html.replace(/(<input\b[^>]*name=["']csrfmiddlewaretoken["'][^>]*value=["'])[^"']*/gi, "$1");
    if (blockSignatures.get(node) === signature) return;
    blockSignatures.set(node, signature);
    node.querySelectorAll(".dk-transition-old").forEach(old => { outgoing.delete(old); old.remove(); });
    let ghost;
    if (enabled() && node.children.length && !node.querySelector("canvas, video, audio")) {
      ghost = document.createElement("div");
      ghost.className = "dk-transition-old";
      ghost.inert = true;
      ghost.setAttribute("aria-hidden", "true");
      for (const child of node.childNodes) ghost.append(child.cloneNode(true));
      ghost.querySelectorAll("*").forEach(child => {
        child.removeAttribute("id"); child.removeAttribute("autofocus");
        for (const attr of [...child.attributes]) if (attr.name.startsWith("data-")) child.removeAttribute(attr.name);
        child.classList.remove("js-carrito-contador", "js-en-carrito");
      });
      ghost.querySelectorAll(".touch-ripple").forEach(wave => wave.remove());
    }
    node.innerHTML = html;
    if (ghost) {
      node.classList.add("dk-transition-host");
      node.append(ghost); outgoing.add(ghost);
      const exit = animate(ghost, [{ opacity: .9, translate: "0 0" }, { opacity: 0, translate: "0 -6px" }], { duration: 320, easing: "cubic-bezier(.16,1,.3,1)" });
      const remove = () => { ghost.remove(); outgoing.delete(ghost); if (!node.querySelector(".dk-transition-old")) node.classList.remove("dk-transition-host"); };
      exit?.finished.then(remove, remove);
      // Cada hijo conserva su transform para el seguimiento reactivo.
      [...node.children].filter(child => child !== ghost).forEach(child => animate(child, [{ opacity: .3, translate: "0 8px" }, { opacity: 1, translate: "0 0" }], { duration: 460, easing: "cubic-bezier(.16,1,.3,1)" }));
    }
    surfaces.forEach((item, surface) => { if (!surface.isConnected) surfaces.delete(surface); });
    document.dispatchEvent(new CustomEvent("dk:content", { detail: { node, serial: ++replacementSerial } }));
  }

  const counters = new WeakMap();
  function counter(node, number) {
    const previous = counters.get(node);
    if (previous) cancelAnimationFrame(previous.frame);
    const from = Number(node.textContent) || 0;
    node.setAttribute("aria-label", String(number));
    if (!enabled() || from === number) { node.textContent = number; return; }
    const state = { frame: 0 };
    const start = performance.now();
    function step(time) {
      const progress = Math.min(1, (time - start) / 340);
      node.textContent = Math.round(from + (number - from) * (1 - (1 - progress) ** 3));
      if (progress < 1 && enabled() && node.isConnected) state.frame = requestAnimationFrame(step);
      else { node.textContent = number; counters.delete(node); }
    }
    state.frame = requestAnimationFrame(step); counters.set(node, state);
  }
  document.addEventListener("dk:respuesta", event => {
    const { form, datos } = event.detail;
    const node = form.closest(".tarjeta-plato, .tarjeta-pedido") || form;
    const ok = datos.ok !== false && datos.nivel !== "danger";
    animate(node, ok ? [{ filter: "brightness(1)" }, { filter: "brightness(1.04)" }, { filter: "brightness(1)" }] : [{ translate: "0 0" }, { translate: "-4px 0" }, { translate: "4px 0" }, { translate: "0 0" }], { duration: ok ? 380 : 260 });
  });
  document.addEventListener("submit", event => {
    if (!event.target.matches(".needs-validation") || event.target.checkValidity()) return;
    animate(event.target, [{ translate: "0 0" }, { translate: "-4px 0" }, { translate: "4px 0" }, { translate: "0 0" }], { duration: 260 });
  });
  document.addEventListener("shown.bs.collapse", event => {
    if (["navPrincipal", "navRestaurante"].includes(event.target.id)) animate(event.target, [{ translate: "0 -10px", opacity: .3 }, { translate: "0 0", opacity: 1 }], { duration: 320, easing: "cubic-bezier(.16,1,.3,1)" });
  });
  document.addEventListener("pointerdown", event => {
    const sidebar = document.querySelector("#navPrincipal.show, #navRestaurante.show");
    if (sidebar && !sidebar.contains(event.target) && !event.target.closest(".sidebar-toggle, .restaurant-nav-toggle")) bootstrap.Collapse.getOrCreateInstance(sidebar, { toggle: false }).hide();
  });
  document.addEventListener("keydown", event => {
    const sidebar = document.querySelector("#navPrincipal.show, #navRestaurante.show");
    if (event.key === "Escape" && sidebar?.classList.contains("show")) {
      bootstrap.Collapse.getOrCreateInstance(sidebar, { toggle: false }).hide();
      document.querySelector(sidebar.id === "navRestaurante" ? ".restaurant-nav-toggle" : ".sidebar-toggle")?.focus();
    }
  });
  window.KitchenUI = { replace, counter, animate };
})();
