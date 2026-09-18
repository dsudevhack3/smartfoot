/**
 * SMARTFOOT Interactive Trends & Telemetry History Charts Manager (Chart.js)
 */

window.SmartfootChartsManager = {
  tempChart: null,
  pressureChart: null,
  gaitChart: null,

  init: function(range = 'week') {
    this.fetchAndRender(range);
  },

  fetchAndRender: function(range) {
    fetch(`/patient/api/trends?range=${range}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.renderTempChart(data.labels, data.temp_diffs);
          this.renderPressureChart(data.labels, data.peak_pressures);
          this.renderGaitChart(data.labels, data.gait_asymmetries, data.risk_scores);
        }
      })
      .catch(err => console.error('[TrendsChart] Error loading telemetry trends:', err));
  },

  renderTempChart: function(labels, tempDiffs) {
    const ctx = document.getElementById('chart-temperature');
    if (!ctx) return;

    if (this.tempChart) this.tempChart.destroy();

    this.tempChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Temperature Asymmetry (Δ°C)',
          data: tempDiffs,
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#06b6d4'
        }]
      },
      options: this.getCommonOptions('Temperature Difference (°C)')
    });
  },

  renderPressureChart: function(labels, peakPressures) {
    const ctx = document.getElementById('chart-pressure');
    if (!ctx) return;

    if (this.pressureChart) this.pressureChart.destroy();

    this.pressureChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Peak Plantar Pressure (kPa)',
          data: peakPressures,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#ef4444'
        }]
      },
      options: this.getCommonOptions('Pressure (kPa)')
    });
  },

  renderGaitChart: function(labels, asymmetries, riskScores) {
    const ctx = document.getElementById('chart-gait');
    if (!ctx) return;

    if (this.gaitChart) this.gaitChart.destroy();

    this.gaitChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Gait Asymmetry (%)',
            data: asymmetries,
            borderColor: '#f59e0b',
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 3
          },
          {
            label: 'Composite Risk Score (0-100)',
            data: riskScores,
            borderColor: '#10b981',
            borderDash: [5, 5],
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 3
          }
        ]
      },
      options: this.getCommonOptions('Value')
    });
  },

  getCommonOptions: function(yTitle) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#9ca3af', font: { family: 'Plus Jakarta Sans', size: 12 } }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#1f2937',
          titleColor: '#fff',
          bodyColor: '#e5e7eb',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#6b7280',
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 8
          }
        },
        y: {
          title: { display: true, text: yTitle, color: '#9ca3af' },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#6b7280' }
        }
      }
    };
  }
};
