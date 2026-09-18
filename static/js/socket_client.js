/**
 * SMARTFOOT SocketIO Client Manager
 * Handles auto-reconnect with backoff, room subscription, and connection status UI updates.
 */

class SmartfootSocketClient {
  constructor(patientId) {
    this.patientId = patientId;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.baseDelay = 1000; // 1 second
    this.lastReceivedTimestamp = Date.now();

    if (this.patientId) {
      this.initSocket();
      this.startLastUpdatedTicker();
    }
  }

  initSocket() {
    console.log(`[SmartfootSocket] Connecting to server for Patient #${this.patientId}...`);
    this.socket = io({
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.baseDelay,
      reconnectionDelayMax: 10000,
      timeout: 20000
    });

    this.socket.on('connect', () => {
      console.log('[SmartfootSocket] Connected successfully!');
      this.reconnectAttempts = 0;
      this.updateStatusPill(true);

      // Join patient room
      this.socket.emit('join_patient_room', { patient_id: this.patientId });
    });

    this.socket.on('disconnect', (reason) => {
      console.warn(`[SmartfootSocket] Disconnected: ${reason}`);
      this.updateStatusPill(false);
    });

    this.socket.on('reconnect_attempt', (attempt) => {
      console.log(`[SmartfootSocket] Reconnecting (Attempt ${attempt})...`);
    });

    // Listen for live telemetry payload
    this.socket.on('telemetry_update', (data) => {
      if (data.patient_id == this.patientId) {
        this.lastReceivedTimestamp = Date.now();
        this.handleTelemetryData(data);
      }
    });
  }

  updateStatusPill(isConnected) {
    const pill = document.getElementById('connection-status-pill');
    const pillText = document.getElementById('connection-status-text');
    const pulseDot = document.getElementById('connection-pulse-dot');

    if (!pill) return;

    if (isConnected) {
      pill.classList.remove('disconnected');
      if (pillText) pillText.textContent = 'Sensor Connected | Streaming live';
      if (pulseDot) pulseDot.classList.remove('red');
    } else {
      pill.classList.add('disconnected');
      if (pillText) pillText.textContent = 'Disconnected | Showing last known reading';
      if (pulseDot) pulseDot.classList.add('red');
    }
  }

  startLastUpdatedTicker() {
    setInterval(() => {
      const ticker = document.getElementById('last-updated-ticker');
      if (ticker && this.lastReceivedTimestamp) {
        const secondsAgo = Math.floor((Date.now() - this.lastReceivedTimestamp) / 1000);
        ticker.textContent = `Updated ${secondsAgo}s ago`;
      }
    }, 1000);
  }

  handleTelemetryData(data) {
    // 1. Update Stat Cards
    const tempLeftEl = document.getElementById('stat-temp-left');
    const tempRightEl = document.getElementById('stat-temp-right');
    const tempDiffEl = document.getElementById('stat-temp-diff');
    const peakPressureEl = document.getElementById('stat-peak-pressure');
    const gaitSymEl = document.getElementById('stat-gait-sym');

    if (tempLeftEl) tempLeftEl.textContent = `${data.temperature_left}°C`;
    if (tempRightEl) tempRightEl.textContent = `${data.temperature_right}°C`;
    if (tempDiffEl) tempDiffEl.textContent = `Δ ${data.temp_diff}°C`;

    if (peakPressureEl && data.pressure_zones) {
      const maxP = Math.max(...Object.values(data.pressure_zones));
      peakPressureEl.textContent = `${maxP.toFixed(1)} kPa`;
    }

    if (gaitSymEl && data.gait_data) {
      const sym = Math.max(0, 100 - data.gait_data.asymmetry).toFixed(1);
      gaitSymEl.textContent = `${sym}%`;
    }

    // 2. Update Foot Heatmap SVG
    if (window.FootPressureMap && data.pressure_zones) {
      window.FootPressureMap.update(data.pressure_zones);
    }

    // 3. Update Risk Prediction Gauge & Breakdown
    if (window.RiskGaugeRenderer) {
      window.RiskGaugeRenderer.update(data.risk_score, data.risk_level, data.risk_takeaway, data.risk_factors);
    }
  }
}

// Global initialization helper
window.initSmartfootSocket = function(patientId) {
  window.smartfootSocket = new SmartfootSocketClient(patientId);
};
