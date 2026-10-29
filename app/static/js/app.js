/* Utilidades compartidas: colores de riesgo, formatos y gráficos (español / inglés). */
const LANG = (document.documentElement.lang || "es").slice(0, 2);
const LEVEL_COLORS = { bajo: "#4F8A6B", moderado: "#D9A21B", alto: "#D9722B", critico: "#B3261E" };
const LEVEL_LABELS = LANG === "en"
  ? { bajo: "Low", moderado: "Moderate", alto: "High", critico: "Critical" }
  : { bajo: "Bajo", moderado: "Moderado", alto: "Alto", critico: "Crítico" };
const MONTHS = LANG === "en"
  ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  : ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const TXT = LANG === "en"
  ? { today: "Today", rain: "Rain (mm)", tmax: "High (°C)", tmin: "Low (°C)" }
  : { today: "Hoy", rain: "Lluvia (mm)", tmax: "Máxima (°C)", tmin: "Mínima (°C)" };

function fmtDay(iso) {
  const d = new Date(iso + "T12:00:00");
  return LANG === "en" ? MONTHS[d.getMonth()] + " " + d.getDate() : d.getDate() + " " + MONTHS[d.getMonth()];
}

if (window.Chart) {
  Chart.defaults.font.family = '"Public Sans Variable", system-ui, sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = "#4A5F63";
  Chart.defaults.borderColor = "rgba(19,38,43,0.08)";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.tooltip.backgroundColor = "#0A2E35";
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.maintainAspectRatio = false;
}

/* Línea vertical que marca el día de hoy en las series de clima. */
const todayLine = {
  id: "todayLine",
  afterDatasetsDraw(chart, _args, opts) {
    if (opts.index == null || opts.index < 0) return;
    const x = chart.scales.x.getPixelForValue(opts.index);
    const { top, bottom } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.strokeStyle = opts.color || "#13262B";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = opts.color || "#13262B";
    ctx.font = '600 11px "Public Sans Variable", sans-serif';
    ctx.fillText(TXT.today, x + 6, top + 12);
    ctx.restore();
  },
};

/* Temperatura (líneas) y lluvia (barras) con pronóstico en trazo punteado. */
function buildClimateChart(canvas, s, opts = {}) {
  const firstFc = s.forecast.findIndex(Boolean);
  const todayIdx = firstFc === -1 ? s.days.length - 1 : firstFc - 1;
  const light = !!opts.light;
  const ink = light ? "#EAF3F2" : "#13262B";
  const dash = (ctx) => (firstFc !== -1 && ctx.p0DataIndex >= todayIdx ? [5, 4] : undefined);
  return new Chart(canvas, {
    data: {
      labels: s.days.map(fmtDay),
      datasets: [
        { type: "bar", label: TXT.rain, data: s.rain, yAxisID: "y1", backgroundColor: light ? "rgba(214,232,231,.55)" : "rgba(23,96,107,.35)", borderRadius: 2, order: 3 },
        { type: "line", label: TXT.tmax, data: s.tmax, yAxisID: "y", borderColor: "#E0A526", backgroundColor: "#E0A526", borderWidth: 2.5, pointRadius: 0, tension: 0.3, segment: { borderDash: dash }, order: 1 },
        { type: "line", label: TXT.tmin, data: s.tmin, yAxisID: "y", borderColor: light ? "#9CC9CE" : "#1F7480", backgroundColor: light ? "#9CC9CE" : "#1F7480", borderWidth: 2, pointRadius: 0, tension: 0.3, segment: { borderDash: dash }, order: 2 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: ink }, grid: { display: false } },
        y: { position: "left", title: { display: true, text: "°C", color: ink }, ticks: { color: ink }, grid: { color: light ? "rgba(255,255,255,.12)" : undefined } },
        y1: { position: "right", title: { display: true, text: "mm", color: ink }, ticks: { color: ink }, grid: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { position: "bottom", labels: { color: ink } }, todayLine: { index: todayIdx, color: ink } },
    },
    plugins: [todayLine],
  });
}

/* Menú móvil. */
(function () {
  const btn = document.getElementById("menu-btn");
  const side = document.getElementById("sidebar");
  const scrim = document.getElementById("scrim");
  if (!btn || !side) return;
  function set(open) {
    side.classList.toggle("hidden", !open);
    side.classList.toggle("flex", open);
    scrim.classList.toggle("hidden", !open);
    btn.setAttribute("aria-expanded", String(open));
  }
  btn.addEventListener("click", () => set(side.classList.contains("hidden")));
  scrim.addEventListener("click", () => set(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") set(false); });
})();
