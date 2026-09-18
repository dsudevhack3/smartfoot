/**
 * SMARTFOOT Anatomical Foot Pressure SVG Heatmap Renderer
 * Maps 12 bilateral zone pressure readings (kPa) to soft radial gradients (Blue -> Green -> Yellow -> Red)
 */

window.FootPressureMap = {
  // Pressure threshold mapping (kPa)
  getColorForPressure: function(kPa) {
    if (kPa < 25.0) {
      // Cool Blue / Teal (<25 kPa)
      return { fill: '#0066ff', glow: 'rgba(0, 102, 255, 0.4)' };
    } else if (kPa < 50.0) {
      // Normal Green (25-50 kPa)
      return { fill: '#10b981', glow: 'rgba(16, 185, 129, 0.4)' };
    } else if (kPa < 70.0) {
      // Warning Yellow / Amber (50-70 kPa)
      return { fill: '#f59e0b', glow: 'rgba(245, 158, 11, 0.5)' };
    } else {
      // Critical Red (>70 kPa)
      return { fill: '#ef4444', glow: 'rgba(239, 68, 68, 0.7)' };
    }
  },

  update: function(zones) {
    if (!zones) return;

    for (const [zoneKey, kPa] of Object.entries(zones)) {
      const circleEl = document.getElementById(`sensor-node-${zoneKey}`);
      const glowEl = document.getElementById(`sensor-glow-${zoneKey}`);
      const valEl = document.getElementById(`sensor-val-${zoneKey}`);

      if (circleEl) {
        const style = this.getColorForPressure(kPa);
        circleEl.setAttribute('fill', style.fill);
        if (glowEl) {
          glowEl.setAttribute('fill', style.glow);
          glowEl.setAttribute('r', Math.min(32, Math.max(16, kPa * 0.4)));
        }
      }
      if (valEl) {
        valEl.textContent = `${Math.round(kPa)}k`;
      }
    }
  }
};
