/* Navegación de la presentación: teclado, clic, gestos táctiles, URL (#n), notas y tema. */
(function () {
  const stage = document.getElementById("stage");
  const slides = Array.from(document.querySelectorAll(".slide"));
  const progress = document.getElementById("progress");
  const num = document.getElementById("slideNum");
  const notes = document.getElementById("notes");
  const notesText = document.getElementById("notesText");
  let current = 0;

  function fit() {
    const s = Math.min(window.innerWidth / 1280, window.innerHeight / 720) * 0.96;
    stage.style.transform = `scale(${s})`;
  }

  function go(i, fromHash) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((sl, k) => {
      sl.classList.toggle("active", k === i);
      sl.classList.toggle("prev", k < i);
    });
    current = i;
    progress.style.width = `${((i + 1) / slides.length) * 100}%`;
    num.textContent = `${i + 1} / ${slides.length}`;
    const note = slides[i].querySelector("aside.speaker");
    notesText.textContent = note ? note.textContent : "Sin notas para esta diapositiva.";
    if (!fromHash) history.replaceState(null, "", `#${i + 1}`);
    // espera a que la diapositiva sea visible para que Chart.js mida bien el canvas
    requestAnimationFrame(() => window.Charts.renderIn(slides[i]));
  }

  const next = () => go(current + 1);
  const prev = () => go(current - 1);

  function toggleTheme() {
    const root = document.documentElement;
    const light = root.getAttribute("data-theme") !== "light";
    if (light) root.setAttribute("data-theme", "light");
    else root.removeAttribute("data-theme");
    try { localStorage.setItem("tema", light ? "light" : "dark"); } catch (e) { /* sin almacenamiento */ }
    window.Charts.rerender(slides[current]);
  }

  function toggleFull() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }

  document.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    switch (e.key) {
      case "ArrowRight": case "ArrowDown": case "PageDown": case " ": case "Enter": e.preventDefault(); next(); break;
      case "ArrowLeft": case "ArrowUp": case "PageUp": case "Backspace": e.preventDefault(); prev(); break;
      case "Home": go(0); break;
      case "End": go(slides.length - 1); break;
      case "f": case "F": toggleFull(); break;
      case "n": case "N": notes.classList.toggle("show"); break;
      case "t": case "T": toggleTheme(); break;
    }
  });

  // gestos táctiles
  let x0 = null;
  document.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (x0 == null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) (dx < 0 ? next : prev)();
    x0 = null;
  });

  document.getElementById("btnPrev").onclick = prev;
  document.getElementById("btnNext").onclick = next;
  document.getElementById("btnNotes").onclick = () => notes.classList.toggle("show");
  document.getElementById("btnTheme").onclick = toggleTheme;
  document.getElementById("btnFull").onclick = toggleFull;

  window.addEventListener("resize", fit);
  window.addEventListener("hashchange", () => go(parseInt(location.hash.slice(1), 10) - 1 || 0, true));
  window.addEventListener("beforeprint", () => window.Charts.renderAll());

  // ayuda que se desvanece
  setTimeout(() => { const h = document.getElementById("help"); if (h) h.style.opacity = "0"; }, 4500);

  if (/light/.test(location.search)) document.documentElement.setAttribute("data-theme", "light");
  if (/static/.test(location.search)) {
    document.documentElement.classList.add("static");
  }
  try { if (localStorage.getItem("tema") === "light") document.documentElement.setAttribute("data-theme", "light"); } catch (e) { /* nada */ }
  fit();
  // se espera a las fuentes para que Chart.js mida bien las etiquetas
  const start = () => { window.Charts.init(); go((parseInt(location.hash.slice(1), 10) || 1) - 1, true); };
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(start, start);
})();
