/**
 * SMARTFOOT 8-Zone Bilateral Insole Pressure Heatmap Renderer
 *
 * Zone keys:
 *   Left:  L_toe (L3), L_met (L4), L_arch (L2), L_heel (L1)
 *   Right: R_toe (R3), R_met (R4), R_arch (R2), R_heel (R1)
 *
 * Color scale (matches reference image gradient bar):
 *   < 25 kPa  → Cyan   (#06b6d4)  Low
 *   25–50 kPa → Green  (#10b981)  Normal
 *   50–70 kPa → Amber  (#f59e0b)  Warning
 *   > 70 kPa  → Pink   (#f43f8c)  Critical
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
   * Update the insole SVG sensor nodes and value labels for all 8 zones.
   * @param {Object} zones  e.g. {L_toe: 42.5, L_met: 49.0, L_arch: 28.0, L_heel: 42.0, ...}
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
