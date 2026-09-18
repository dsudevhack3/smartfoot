/**
 * SMARTFOOT Risk Score Ring Gauge & Factor Breakdown Renderer
 */

window.RiskGaugeRenderer = {
  update: function(score, level, takeaway, factors) {
    // 1. Update Gauge Ring
    const progressRing = document.getElementById('risk-gauge-progress');
    const scoreText = document.getElementById('risk-gauge-score');
    const levelBadge = document.getElementById('risk-level-badge');
    const takeawayText = document.getElementById('risk-takeaway-text');

    if (scoreText) scoreText.textContent = Math.round(score);

    if (progressRing) {
      // Circumference of r=70 circle is 2 * PI * 70 = 440
      const strokeDashoffset = 440 - (440 * Math.min(100, Math.max(0, score))) / 100;
      progressRing.style.strokeDashoffset = strokeDashoffset;

      if (level === 'HIGH') {
        progressRing.style.stroke = '#ef4444';
      } else if (level === 'MODERATE') {
        progressRing.style.stroke = '#f59e0b';
      } else {
        progressRing.style.stroke = '#10b981';
      }
    }

    if (levelBadge) {
      levelBadge.textContent = level;
      levelBadge.className = `risk-level-badge ${level}`;
    }

    if (takeawayText && takeaway) {
      takeawayText.textContent = takeaway;
    }

    // 2. Update 40/30/30 Factor Breakdown Cards
    if (factors) {
      // Pressure Factor (40%)
      const p = factors.pressure;
      const pBar = document.getElementById('factor-bar-pressure');
      const pStatus = document.getElementById('factor-status-pressure');
      const pDesc = document.getElementById('factor-desc-pressure');
      if (pBar) pBar.style.width = `${p.score}%`;
      if (pStatus) pStatus.textContent = `${p.status} (${p.score}/100)`;
      if (pDesc) pDesc.textContent = p.explanation;

      // Temperature Factor (30%)
      const t = factors.temperature;
      const tBar = document.getElementById('factor-bar-temp');
      const tStatus = document.getElementById('factor-status-temp');
      const tDesc = document.getElementById('factor-desc-temp');
      if (tBar) tBar.style.width = `${t.score}%`;
      if (tStatus) tStatus.textContent = `${t.status} (${t.score}/100)`;
      if (tDesc) tDesc.textContent = t.explanation;

      // Gait Factor (30%)
      const g = factors.gait;
      const gBar = document.getElementById('factor-bar-gait');
      const gStatus = document.getElementById('factor-status-gait');
      const gDesc = document.getElementById('factor-desc-gait');
      if (gBar) gBar.style.width = `${g.score}%`;
      if (gStatus) gStatus.textContent = `${g.status} (${g.score}/100)`;
      if (gDesc) gDesc.textContent = g.explanation;
    }
  }
};
