/* Gráficas de la presentación (Chart.js 4).
   Los datos vienen de js/data.js, generado por analisis/analisis.py.
   Cada gráfica se crea cuando su diapositiva se muestra, para que la animación se vea en vivo. */
(function () {
  const D = window.DATA;
  const instances = {};

  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function wrap(text, max) {
    const words = String(text).split(" ");
    const lines = [];
    let line = "";
    for (const w of words) {
      if ((line + " " + w).trim().length > max && line) { lines.push(line); line = w; }
      else line = (line + " " + w).trim();
    }
    if (line) lines.push(line);
    return lines;
  }

  function applyDefaults() {
    Chart.defaults.font.family = "Inter, 'Segoe UI', system-ui, sans-serif";
    Chart.defaults.font.size = 13;
    Chart.defaults.color = css("--text-secondary");
    Chart.defaults.borderColor = css("--grid");
    Chart.defaults.maintainAspectRatio = false;
    if (document.documentElement.classList.contains("static")) Chart.defaults.animation = false;
    else Object.assign(Chart.defaults.animation, { duration: 900, easing: "easeOutQuart" });
    Chart.defaults.plugins.legend.display = false;
    Object.assign(Chart.defaults.plugins.tooltip, {
      backgroundColor: css("--surface-1"),
      titleColor: css("--text-primary"),
      bodyColor: css("--text-secondary"),
      borderColor: css("--border"),
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      displayColors: true,
      boxPadding: 4,
    });
  }

  /* Etiquetas de valor al final de cada barra (texto en tinta, nunca en el color de la serie) */
  const valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw(chart, _args, opts) {
      if (!opts || !opts.format) return;
      const { ctx } = chart;
      ctx.save();
      ctx.font = `600 ${opts.size || 13}px Inter, system-ui, sans-serif`;
      chart.data.datasets.forEach((ds, di) => {
        const meta = chart.getDatasetMeta(di);
        if (meta.hidden) return;
        meta.data.forEach((el, i) => {
          const v = ds.data[i];
          if (v == null || (opts.skipZero && !v)) return;
          const txt = opts.format(v, i, di);
          if (!txt) return;
          const horizontal = chart.options.indexAxis === "y";
          const p = el.getProps(["x", "y", "base", "width", "height"], true);
          if (opts.inside) {
            const w = horizontal ? Math.abs(p.x - p.base) : p.width;
            if (w < ctx.measureText(txt).width + 10) return;
            ctx.fillStyle = "#ffffff";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(txt, horizontal ? (p.x + p.base) / 2 : p.x, horizontal ? p.y : (p.y + p.base) / 2);
          } else {
            ctx.fillStyle = css("--text-primary");
            if (horizontal) {
              ctx.textAlign = "left"; ctx.textBaseline = "middle";
              ctx.fillText(txt, p.x + 8, p.y);
            } else {
              ctx.textAlign = "center"; ctx.textBaseline = "bottom";
              ctx.fillText(txt, p.x, p.y - 6);
            }
          }
        });
      });
      ctx.restore();
    },
  };
  Chart.register(valueLabels);

  const pctFmt = (v) => `${Math.round(v)} %`;

  /* Barras horizontales a partir de un bloque {items:[{label,n,pct,otro}], na} */
  function hbar(id, bloque, { highlight = 1, wrapAt = 30, includeNA = true } = {}) {
    const items = bloque.items.filter((r) => r.n > 0);
    if (includeNA && bloque.na) items.push({ label: "N/A: No aplica", n: bloque.na, pct: +(100 * bloque.na / D.n).toFixed(1), otro: true });
    const colors = items.map((r, i) => (r.otro ? css("--neutral") : i < highlight ? css("--series-1") : css("--bar-muted")));
    const max = Math.max(...items.map((r) => r.pct));
    return {
      type: "bar",
      data: {
        labels: items.map((r) => wrap(r.label, wrapAt)),
        datasets: [{ data: items.map((r) => r.pct), backgroundColor: colors, borderRadius: 4, borderSkipped: "start", barPercentage: 0.78, categoryPercentage: 0.9 }],
      },
      options: {
        indexAxis: "y",
        layout: { padding: { left: 4, right: 56 } },
        scales: {
          x: { display: false, min: 0, max: max * 1.08 },
          y: { grid: { display: false }, border: { display: false }, ticks: { autoSkip: false, color: css("--text-primary"), font: { size: items.length > 8 ? 12 : 13 } } },
        },
        plugins: {
          valueLabels: { format: pctFmt },
          tooltip: { callbacks: { title: (c) => items[c[0].dataIndex].label, label: (c) => ` ${items[c.dataIndex].n} personas (${items[c.dataIndex].pct} %)` } },
        },
      },
    };
  }

  const builders = {
    "c-error": () => {
      const pts = [];
      for (let n = 20; n <= 420; n += 4) pts.push({ x: n, y: 196 * Math.sqrt(0.25 / n) });
      const mark = [
        { x: D.n, y: D.muestreo.error_logrado, lbl: `n = ${D.n} → ±${D.muestreo.error_logrado} %` },
        { x: D.muestreo.n_para_5, y: 5, lbl: `n = ${D.muestreo.n_para_5} → ±5 %` },
      ];
      return {
        type: "line",
        data: {
          datasets: [
            { data: pts, borderColor: css("--series-1"), borderWidth: 2, pointRadius: 0, pointHoverRadius: 0, tension: 0.3, fill: { target: "origin", above: css("--accent-soft") } },
            { type: "scatter", data: mark, pointRadius: 7, pointHoverRadius: 9, pointBackgroundColor: [css("--series-2"), css("--series-3")], pointBorderColor: css("--surface-2"), pointBorderWidth: 2 },
          ],
        },
        options: {
          interaction: { mode: "nearest", intersect: false },
          scales: {
            x: { type: "linear", min: 20, max: 420, title: { display: true, text: "Tamaño de muestra (n)" }, grid: { display: false } },
            y: { min: 0, max: 24, title: { display: true, text: "Margen de error (± %)" }, ticks: { callback: (v) => v + " %" } },
          },
          plugins: {
            tooltip: { filter: (c) => c.datasetIndex === 1, callbacks: { title: () => "", label: (c) => " " + mark[c.dataIndex].lbl } },
          },
        },
        plugins: [{
          id: "markLabels",
          afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(1);
            ctx.save();
            ctx.font = "600 13px Inter, system-ui, sans-serif";
            ctx.fillStyle = css("--text-primary");
            meta.data.forEach((el, i) => {
              ctx.textAlign = i === 0 ? "left" : "right";
              ctx.fillText(mark[i].lbl, el.x + (i === 0 ? 12 : -4), el.y - 14);
            });
            ctx.restore();
          },
        }],
      };
    },

    "c-facultad": () => {
      const f = D.facultad;
      const cfg = hbar("c-facultad", { items: f.labels.map((l, i) => ({ label: l, n: f.n[i], pct: f.pct[i] })), na: 0 }, { highlight: 1, wrapAt: 26 });
      cfg.options.plugins.valueLabels.format = (v, i) => `${f.n[i]}`;
      return cfg;
    },

    "c-semestre": () => {
      const s = D.semestre;
      const top = Math.max(...s.n);
      return {
        type: "bar",
        data: { labels: s.labels, datasets: [{ data: s.n, backgroundColor: s.n.map((v) => (v === top ? css("--series-1") : css("--bar-muted"))), borderRadius: 4, borderSkipped: "start", barPercentage: 0.75 }] },
        options: {
          layout: { padding: { top: 22 } },
          scales: { y: { display: false, beginAtZero: true }, x: { grid: { display: false }, border: { display: false }, ticks: { color: css("--text-primary") } } },
          plugins: { valueLabels: { format: (v) => v }, tooltip: { callbacks: { title: (c) => `${c[0].label} semestre`, label: (c) => ` ${c.raw} personas` } } },
        },
      };
    },

    "c-frecuencia": () => {
      const it = D.frecuencia.items;
      const colors = [css("--ord-1"), css("--ord-2"), css("--ord-3"), css("--ord-4")];
      return {
        type: "doughnut",
        data: { labels: it.map((r) => r.label), datasets: [{ data: it.map((r) => r.n), backgroundColor: colors, borderColor: css("--surface-2"), borderWidth: 3, hoverOffset: 10 }] },
        options: {
          cutout: "58%",
          rotation: -90,
          layout: { padding: 10 },
          plugins: {
            legend: { display: true, position: "right", labels: { color: css("--text-primary"), boxWidth: 14, boxHeight: 14, padding: 16, font: { size: 14 },
              generateLabels: (chart) => it.map((r, i) => ({ text: `${r.label}  ·  ${r.n} (${Math.round(r.pct)} %)`, fillStyle: colors[i], strokeStyle: colors[i], fontColor: css("--text-primary"), index: i })) } },
            tooltip: { callbacks: { label: (c) => ` ${c.raw} personas (${it[c.dataIndex].pct} %)` } },
          },
        },
        plugins: [{
          id: "centerText",
          afterDraw(chart) {
            const { ctx } = chart;
            const m = chart.getDatasetMeta(0).data[0];
            if (!m) return;
            ctx.save();
            ctx.textAlign = "center";
            ctx.fillStyle = css("--text-primary");
            ctx.font = "700 34px 'Space Grotesk', system-ui, sans-serif";
            ctx.fillText(D.n, m.x, m.y + 4);
            ctx.fillStyle = css("--text-muted");
            ctx.font = "500 13px Inter, system-ui, sans-serif";
            ctx.fillText("respuestas", m.x, m.y + 24);
            ctx.restore();
          },
        }],
      };
    },

    "c-motivos": () => hbar("c-motivos", D.motivos, { highlight: 1, wrapAt: 26 }),
    "c-horario": () => hbar("c-horario", D.horario, { highlight: 1, wrapAt: 24 }),
    "c-asignaturas": () => hbar("c-asignaturas", D.asignaturas, { highlight: 3, wrapAt: 26 }),
    "c-actividades": () => hbar("c-actividades", D.actividades, { highlight: 1, wrapAt: 32 }),
    "c-impacto-rend": () => hbar("c-impacto-rend", { ...D.impacto_rend, items: D.impacto_rend.items.map((r) => ({ ...r })) }, { highlight: 2, wrapAt: 22 }),
    "c-impacto-psico": () => {
      // Las 3 opciones con 1 respuesta cada una se agrupan para que la gráfica respire
      const it = D.impacto_psico.items.filter((r) => r.n > 1).sort((a, b) => b.n - a.n);
      const small = D.impacto_psico.items.filter((r) => r.n === 1);
      if (small.length) it.push({ label: "Otras (desconexión, temor, incomodidad)", n: small.length, pct: +(100 * small.length / D.n).toFixed(1), otro: true });
      return hbar("c-impacto-psico", { items: it, na: D.impacto_psico.na }, { highlight: 1, wrapAt: 24 });
    },
    "c-factores": () => hbar("c-factores", D.factores, { highlight: 2, wrapAt: 26 }),

    "c-gpa": () => {
      const g = D.gpa_por_freq;
      // jitter determinista para que los puntos no se monten
      const pts = [];
      g.forEach((grp, gi) => grp.valores.forEach((v, k) => pts.push({ x: gi + (((k * 37) % 11) / 10 - 0.5) * 0.36, y: v, grp: gi })));
      const means = g.map((grp, gi) => (grp.media == null ? null : { x: gi, y: grp.media }));
      return {
        type: "scatter",
        data: {
          datasets: [
            { data: pts, pointRadius: 6, pointHoverRadius: 8, backgroundColor: css("--series-1") + "b3", borderColor: css("--surface-2"), borderWidth: 1.5 },
            { data: means.filter(Boolean), pointStyle: "line", pointRadius: 38, pointHoverRadius: 38, borderWidth: 3, borderColor: css("--series-2"), backgroundColor: css("--series-2") },
          ],
        },
        options: {
          layout: { padding: { top: 10, right: 10 } },
          scales: {
            x: { type: "linear", min: -0.6, max: 3.6, grid: { display: false },
              afterBuildTicks: (ax) => { ax.ticks = [0, 1, 2, 3].map((v) => ({ value: v })); },
              ticks: { color: css("--text-primary"), callback: (v) => (g[v] ? [g[v].label, `n = ${g[v].n}`] : "") } },
            y: { min: 3.0, max: 5.0, title: { display: true, text: "Promedio acumulado" }, ticks: { stepSize: 0.25, callback: (v) => v.toFixed(2) } },
          },
          plugins: {
            tooltip: { callbacks: { title: () => "", label: (c) => (c.datasetIndex === 1 ? ` Media del grupo: ${c.raw.y.toFixed(2)}` : ` Promedio: ${c.raw.y.toFixed(2)}`) } },
          },
        },
        plugins: [{
          id: "meanLabels",
          afterDatasetsDraw(chart) {
            const { ctx } = chart;
            ctx.save();
            ctx.font = "700 14px Inter, system-ui, sans-serif";
            ctx.fillStyle = css("--text-primary");
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            chart.getDatasetMeta(1).data.forEach((el, i) => {
              ctx.fillText(chart.data.datasets[1].data[i].y.toFixed(2), el.x + 42, el.y);
            });
            ctx.restore();
          },
        }],
      };
    },

    "c-cruce": () => {
      const c = D.cruce_impacto;
      const keep = c.columnas.map((_, j) => c.conteos.some((r) => r[j] > 0));
      const cols = c.columnas.filter((_, j) => keep[j]);
      const totals = c.conteos.map((r) => r.reduce((a, b) => a + b, 0));
      const palette = { "No me afecta": css("--series-1"), "Leve, lo compenso": css("--series-2"), "Depende de la materia": css("--series-3"), "N/A": css("--neutral") };
      const datasets = cols.map((col) => {
        const j = c.columnas.indexOf(col);
        return {
          label: col,
          data: c.conteos.map((r, i) => (100 * r[j]) / totals[i]),
          counts: c.conteos.map((r) => r[j]),
          backgroundColor: palette[col],
          borderColor: css("--surface-2"),
          borderWidth: { right: 2 },
          borderSkipped: false,
          barPercentage: 0.7,
        };
      });
      return {
        type: "bar",
        data: { labels: c.filas.map((f, i) => [f, `n = ${totals[i]}`]), datasets },
        options: {
          indexAxis: "y",
          scales: {
            x: { stacked: true, max: 100, ticks: { callback: (v) => v + " %" }, grid: { color: css("--grid") } },
            y: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { color: css("--text-primary"), font: { size: 13 } } },
          },
          plugins: {
            legend: { display: true, position: "bottom", labels: { color: css("--text-primary"), boxWidth: 12, boxHeight: 12, padding: 18 } },
            valueLabels: { inside: true, skipZero: true, format: (v) => `${Math.round(v)} %` },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${ctx.dataset.counts[ctx.dataIndex]} (${Math.round(ctx.raw)} %)` } },
          },
        },
      };
    },

    "c-material": () => {
      const m = D.material_virtual;
      const colors = ["--div-1", "--div-2", "--div-3", "--div-4", "--div-5"].map(css);
      const names = ["Disminuye mucho", "Disminuye", "Sin efecto", "Aumenta", "Aumenta mucho"];
      return {
        type: "bar",
        data: { labels: m.labels.map((l, i) => [l, names[i]]), datasets: [{ data: m.n, backgroundColor: colors, borderRadius: 4, borderSkipped: "start", barPercentage: 0.72 }] },
        options: {
          layout: { padding: { top: 24 } },
          scales: { y: { display: false, beginAtZero: true }, x: { grid: { display: false }, border: { display: false }, ticks: { color: css("--text-primary"), font: { size: 13 } } } },
          plugins: {
            valueLabels: { format: (v) => `${v}` },
            tooltip: { callbacks: { title: (c) => names[c[0].dataIndex], label: (c) => ` ${c.raw} personas (${Math.round((100 * c.raw) / D.n)} %)` } },
          },
        },
      };
    },
  };

  function renderIn(slide) {
    slide.querySelectorAll("canvas[id]").forEach((cv) => {
      if (instances[cv.id] || !builders[cv.id]) return;
      instances[cv.id] = new Chart(cv, builders[cv.id]());
    });
  }

  function destroyAll() {
    Object.keys(instances).forEach((k) => { instances[k].destroy(); delete instances[k]; });
  }

  // Cuadrícula de la portada: un cuadrito por encuestado
  function coverDots() {
    const box = document.getElementById("coverDots");
    if (!box) return;
    const on = D.capan_alguna_vez.n;
    box.innerHTML = Array.from({ length: D.n }, (_, i) => `<i class="${i < on ? "on" : ""}"></i>`).join("");
    box.title = `${on} de ${D.n} encuestados capan clase al menos ocasionalmente`;
  }

  window.Charts = {
    init() { applyDefaults(); coverDots(); },
    renderIn,
    rerender(activeSlide) { destroyAll(); applyDefaults(); renderIn(activeSlide); },
    renderAll() { document.querySelectorAll(".slide").forEach(renderIn); },
  };
})();
