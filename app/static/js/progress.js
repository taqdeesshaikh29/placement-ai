const read = (id) => {
  const el = document.getElementById(id);
  return el ? { el, data: JSON.parse(el.dataset.points) } : null;
};

const percentAxis = { y: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + "%" } } };

const subjects = read("subjectChart");
if (subjects) {
  new Chart(subjects.el, {
    type: "bar",
    data: {
      labels: subjects.data.map((s) => s.subject),
      datasets: [{ label: "Accuracy (%)", data: subjects.data.map((s) => s.accuracy),
                   backgroundColor: "#6366f1", borderRadius: 6 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, scales: percentAxis,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: (ctx) => { const s = subjects.data[ctx.dataIndex]; return `${s.accuracy}% (${s.correct}/${s.attempted} correct)`; },
      } } },
    },
  });
}

const trend = read("trendChart");
if (trend) {
  new Chart(trend.el, {
    type: "line",
    data: {
      labels: trend.data.map((p) => p.label),
      datasets: [{ label: "Quiz accuracy (%)", data: trend.data.map((p) => p.accuracy),
                   borderColor: "#6366f1", backgroundColor: "#6366f133", fill: true, tension: 0.25, pointRadius: 4 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, scales: percentAxis,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: (ctx) => { const p = trend.data[ctx.dataIndex]; return `${p.subject}: ${p.correct}/${p.total} (${p.accuracy}%)`; },
      } } },
    },
  });
}
