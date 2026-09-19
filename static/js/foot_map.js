/**
 * SMARTFOOT Right Insole Plantar Pressure Heatmap Renderer
 *
 * Zone keys (Right Foot Only — 4 FSR Sensors + 1 Thermistor T1):
 *   R_toe (R3) — Medial Forefoot / Big Toe
 *   R_met (R4) — Lateral Forefoot Metatarsal
 *   R_arch (R2) — Midfoot Arch
 *   R_heel (R1) — Heel
 *
 * Color scale (matches reference image gradient bar):
 *   < 35 kPa  → Cyan/Teal  (#279ca8)  Low
 *   35–65 kPa → Emerald    (#27a869)  Normal
 *   65–85 kPa → Amber      (#f59e0b)  Warning
 *   > 85 kPa  → Pink       (#f43f8c)  Critical
 */

window.FootPressureMap = {

  getColorForPressure: function (kPa) {
    if (kPa < 35.0)  return '#279ca8';   // Cyan/Teal (Low/Moderate)
    if (kPa < 65.0)  return '#27a869';   // Emerald Green (Normal)
    if (kPa < 85.0)  return '#f59e0b';   // Amber Warning
    return                '#f43f8c';     // Pink Critical
  },

  getGlowForPressure: function (kPa) {
    if (kPa < 35.0)  return 'rgba(39,156,168,0.75)';
    if (kPa < 65.0)  return 'rgba(39,168,105,0.75)';
    if (kPa < 85.0)  return 'rgba(245,158,11,0.75)';
    return                  'rgba(244,63,140,0.85)';
  },

  /**
   * Update the right insole SVG sensor nodes and value labels.
   * @param {Object} zones  e.g. {R_toe: 42.5, R_met: 49.0, R_arch: 28.0, R_heel: 42.0}
   */
  update: function (zones) {
    if (!zones) return;

    for (const [zoneKey, kPa] of Object.entries(zones)) {
      const nodeEl = document.getElementById(`sensor-node-${zoneKey}`);
      const valEl  = document.getElementById(`sensor-val-${zoneKey}`);

      if (nodeEl) {
        const color = this.getColorForPressure(kPa);
        const glow  = this.getGlowForPressure(kPa);
        nodeEl.setAttribute('fill', color);
        // Apply glow via CSS drop-shadow (works on both rect & circle SVG elements)
        nodeEl.style.filter = `drop-shadow(0 0 10px ${glow})`;
      }
      if (valEl) {
        valEl.textContent = `${Math.round(kPa)}k`;
      }
    }
  }
};
