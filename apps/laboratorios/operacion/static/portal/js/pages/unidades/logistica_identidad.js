/* Mejora progresiva: control de movimiento y orientación dentro de la página. */
(() => {
  "use strict";
  const root = document.querySelector(".logistica-identidad");
  if (!root) return;
  const control = root.querySelector("[data-logistica-motion]");
  const media = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  let manualPause = false;
  const updateMotion = () => {
    const reduced = Boolean(media && media.matches);
    root.classList.toggle("is-motion-paused", manualPause || reduced);
    if (!control) return;
    control.hidden = reduced;
    control.setAttribute("aria-pressed", String(manualPause));
    control.textContent = manualPause ? "Reanudar animaciones" : "Pausar animaciones";
  };
  if (control) control.addEventListener("click", () => { manualPause = !manualPause; updateMotion(); });
  if (media && media.addEventListener) media.addEventListener("change", updateMotion);
  updateMotion();
  if (!("IntersectionObserver" in window)) return;
  const links = Array.from(root.querySelectorAll(".logistica-indice a[href^='#']"));
  const sections = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (!visible.length) return;
    const selected = visible[0].target.id;
    links.forEach(link => {
      if (link.hash === "#" + selected) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }, { rootMargin: "-5% 0px -65% 0px", threshold: 0 });
  sections.forEach(section => observer.observe(section));
})();
