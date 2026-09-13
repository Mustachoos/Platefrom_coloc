/* Standardized notification component (PI-2 US-B1). One rounded rectangle,
   fade + slight descend on entry, 3s hold, fade + retreat on exit. Queued —
   mirrors the overlayQueue/showNextOverlay pattern in tv.js: never shows two
   notifications at once, each gets its own full cycle. */
(function () {
  const HOLD_MS = 3000;
  const TRANSITION_MS = 200; // matches --base

  let container = null;
  const queue = [];
  let showing = false;

  function ensureContainer() {
    if (!container) {
      container = document.createElement("div");
      container.className = "notify-container";
      document.body.appendChild(container);
    }
    return container;
  }

  function showNext() {
    if (showing || queue.length === 0) return;
    showing = true;
    const { text, level } = queue.shift();

    const el = document.createElement("div");
    el.className = "notify notify--" + level;
    el.textContent = text;
    ensureContainer().appendChild(el);

    requestAnimationFrame(() => {
      el.classList.add("is-visible");
    });

    setTimeout(() => {
      el.classList.remove("is-visible");
      setTimeout(() => {
        el.remove();
        showing = false;
        showNext();
      }, TRANSITION_MS);
    }, HOLD_MS);
  }

  const VALID_LEVELS = ["success", "error", "warning", "info"];

  window.notify = function (text, level) {
    queue.push({ text: text, level: VALID_LEVELS.includes(level) ? level : "info" });
    showNext();
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".server-message").forEach(function (node) {
      window.notify(node.dataset.text, node.dataset.level);
      node.remove();
    });
  });
})();
