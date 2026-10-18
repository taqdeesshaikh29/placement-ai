const canvas = document.getElementById("subjectChart");
const subjects = JSON.parse(canvas.dataset.subjects);

new Chart(canvas, {
  type: "bar",
  data: {
    labels: subjects.map((s) => s.subject),
    datasets: [{
      label: "Accuracy (%)",
      data: subjects.map((s) => s.accuracy),
      backgroundColor: "#6366f1",
      borderRadius: 6,
    }],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: { y: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + "%" } } },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const s = subjects[ctx.dataIndex];
            return `${s.accuracy}% (${s.correct}/${s.attempted} correct)`;
          },
        },
      },
    },
  },
});
