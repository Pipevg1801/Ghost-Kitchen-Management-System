"use strict";
// Se resuelve antes de pintar: una elección explícita prevalece sobre el sistema.
(() => {
  const media = matchMedia("(prefers-reduced-motion: reduce)");
  let choice = "auto";
  try { choice = localStorage.getItem("ghost-kitchen-motion") || "auto"; } catch (_) { /* Almacenamiento opcional. */ }
  if (!["auto", "full", "reduced"].includes(choice)) choice = "auto";
  function resolve() {
    const enabled = choice === "full" || (choice === "auto" && !media.matches);
    document.documentElement.dataset.motion = enabled ? "full" : "reduced";
    document.documentElement.dataset.motionChoice = choice;
    document.dispatchEvent(new CustomEvent("dk:motion", { detail: { enabled, choice } }));
  }
  window.KitchenMotion = {
    get enabled() { return document.documentElement.dataset.motion === "full"; },
    get choice() { return choice; },
    setChoice(value) {
      if (!["auto", "full", "reduced"].includes(value)) return;
      choice = value;
      try { localStorage.setItem("ghost-kitchen-motion", choice); } catch (_) { /* La sesión sigue funcionando. */ }
      resolve();
    },
  };
  media.addEventListener("change", resolve);
  resolve();
})();
