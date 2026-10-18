const BRAND = "#0b5cab";
const DANGER = "#d64545";
let occChart = null;
let statsTimer = null;

// Refresh the chart a moment after the bed grid is redrawn (covers local and live changes)
function scheduleStats() {
  clearTimeout(statsTimer);
  statsTimer = setTimeout(refreshStats, 300);
}

new MutationObserver(scheduleStats).observe(grid, { childList: true });

if (me.role !== "nurse") {
  document.getElementById("auditLink").classList.remove("hidden");
}

async function refreshStats() {
  try {
    const stats = await api("/stats/occupancy");
    drawChart(stats);
    showBanner(stats);
    if (wardSelect.value) showForecast(wardSelect.value);
  } catch (e) {
    // Stats are optional. The bed grid keeps working without them.
  }
}

function drawChart(stats) {
  const labels = stats.map(s => s.name);
  const data = stats.map(s => s.pct);
  const colors = stats.map(s => (s.pct >= 90 ? DANGER : BRAND));

  if (!occChart) {
    occChart = new Chart(document.getElementById("occChart"), {
      type: "bar",
      data: { labels, datasets: [{ label: "Occupancy %", data, backgroundColor: colors }] },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const s = stats[ctx.dataIndex];
                return s.pct + "% (" + s.occupied + " of " + s.total + " beds)";
              },
            },
          },
        },
        scales: {
          y: { min: 0, max: 100, ticks: { callback: v => v + "%" } },
        },
      },
    });
  } else {
    occChart.data.labels = labels;
    occChart.data.datasets[0].data = data;
    occChart.data.datasets[0].backgroundColor = colors;
    occChart.update();
  }
}

function showBanner(stats) {
  const banner = document.getElementById("alertBanner");
  const hot = stats.filter(s => s.pct >= 90);
  if (!hot.length) {
    banner.className = "banner hidden";
    banner.textContent = "";
    return;
  }
  banner.textContent =
    "High occupancy: " +
    hot.map(s => s.name + " " + s.pct + "% (" + s.occupied + " of " + s.total + " beds)").join(", ");
  banner.className = "banner";
}

async function showForecast(wardId) {
  const box = document.getElementById("forecast");
  try {
    const f = await api("/forecast/" + wardId);
    box.textContent = f.message + " (estimate from recent trend; staff decide)";
    box.className = "forecast " + f.status;
  } catch (e) {
    box.textContent = "";
    box.className = "forecast hidden";
  }
}