# SMARTFOOT — Full-Stack IoT Diabetic Foot Monitoring System (v3)

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![SocketIO](https://img.shields.io/badge/WebSocket-Flask--SocketIO-teal.svg)](https://flask-socketio.readthedocs.io/)
[![License](https://img.shields.io/badge/License-Research%20%2F%20Educational-orange.svg)]()

**SMARTFOOT** is a complete, full-stack diabetic foot tele-monitoring platform. It combines **ESP32 hardware integration**, real-time **WebSocket telemetry streaming**, per-patient isolated data pipelines, a **deterministic 40/30/30 Risk Engine**, a **deduplicated Alert Engine**, an **anatomical 12-zone bilateral foot pressure SVG heatmap**, and a professional dark-themed healthcare UI for both patients and clinicians.

---

## 💡 System Architecture & Data Pipeline

```
ESP32 sensors (one device per patient) → HTTP POST (device-token authenticated)
             → Flask API (/api/v1/telemetry)
             → resolve device_token → patient_id
             → validation + normalization
             → SQLite database (Telemetry table, tagged with that patient_id)
             → Risk Engine (recalculates patient's score) + Alert Engine (checks thresholds)
             → Flask-SocketIO broadcasts to room `patient_{id}` ONLY
             → Browser UI updates live, no page refresh
```

In demo mode (`DEMO_MODE=True`), **one independent background simulator instance runs per seeded demo patient**, each generating plausible independent readings over time and broadcasting through the exact same Risk Engine → Alert Engine → WebSocket pipeline. Switching from demo simulation to real ESP32 hardware requires zero architectural changes.

---

## 🛠 Tech Stack

- **Backend & Web Server:** Python Flask + Jinja2 templates (single unified application)
- **Database ORM:** SQLite with SQLAlchemy ORM
- **Real-Time Communication:** Flask-SocketIO (WebSocket) with client auto-reconnect & exponential backoff
- **Authentication:** Local Email + OTP (`123456` in demo mode) + Instant Demo Persona Selector
- **Hardware Integration:** ESP32 DevKit, 12-zone FSR pressure sensors, DS18B20 thermal sensors, MPU6050 IMU
- **Frontend & Visualizations:** HTML5, CSS3 (Healthcare Dark Theme System), JavaScript (ES6+), Anatomical SVG Heatmap, Chart.js, Lucide Icons
- **Deployment:** Single Flask app, Gunicorn + Eventlet / Threading worker

---

## 🛡 Authentication & Multi-Patient Isolation

- **Local Email + OTP Login:** Primary authentication flow using an isolated `generate_and_send_otp(email)` function (uses static OTP `123456` in demo mode, ready for a 1-function SMTP swap).
- **Instant Demo Persona Selector:** Quick-login as any seeded demo patient or doctor without completing the OTP form (gated strictly behind `DEMO_MODE=True`).
- **Role-Based Access Control (RBAC):** `PATIENT` role accesses only their own telemetry; `DOCTOR` role accesses only assigned patients.
- **Hardware Device Auth:** Each ESP32 device has a unique `device_token` mapped 1:1 to a `patient_id`. Telemetry POSTs must include a valid device token or are rejected.
- **WebSocket Scoping:** Clients join isolated room `patient_{patient_id}` to prevent cross-patient data leakage.
- **No Unverifiable Compliance Claims:** No Google OAuth and no HIPAA text anywhere in code or UI. Uses defensible wording: *"Encrypted healthcare session • Role-based access control enabled"*.

---

## 📊 Deterministic Risk Engine (0–100)

The Risk Engine calculates a deterministic 0–100 score based on three weighted clinical factors:

1. **Plantar Pressure Deviation (40% Weight):** Peak and average pressure deviation across 12 bilateral zones relative to patient baseline (kPa).
2. **Thermal Asymmetry (30% Weight):** Differential temperature between left and right foot (`abs(temp_left - temp_right)` in °C).
   
### Risk Thresholds
- 🟢 **LOW RISK (< 30):** Baseline metrics healthy. Continue normal daily routine.
- 🟡 **MODERATE RISK (30–60):** Mild pressure/temp elevation. Re-examine foot skin; schedule 3-day follow-up.
- 🔴 **HIGH RISK (> 60):** Focal pressure spike and severe temperature asymmetry. Consult physician promptly.

---

## 🚨 Alert Engine & Deduplication

- **Alert Types:** `HIGH_PRESSURE`, `TEMP_ASYMMETRY`, `GAIT_DEVIATION`, `SENSOR_DISCONNECTED`.
- **Status Lifecycle:** `ACTIVE` → `ACKNOWLEDGED` (doctor-only action) → `RESOLVED`.
- **De-duplication Rule:** Checks for an existing `ACTIVE` alert with matching `patient_id`, `type`, and `region`. Updates existing timestamps and values instead of spawning duplicate rows per telemetry tick.
- **Descriptive Event Titles:** Titles explicitly describe the clinical event (e.g., *"High Pressure Spike — Right 1st Metatarsal"*).

---

## 🎨 UI & Visualization Features

- **Single Centered Card Login:** Max-width ~520px card with OTP input, persona switcher, and medical notice footer.
- **Anatomical 12-Zone Foot Pressure Map:** 6 bilateral sensor points per foot (Heel, Lateral Midfoot, Medial Midfoot, 1st Metatarsal, 5th Metatarsal, Hallux) rendered as soft radial-gradient SVG heatmaps (Blue → Green → Yellow → Red) with live numerical pressure labels (`24k`, `28k`, `32k`, etc.).
- **Risk Ring Gauge Centerpiece:** Animated circular progress ring (0–100), risk level badge, 40/30/30 factor progress bars, and actionable takeaway.
- **Clinical Doctor Console:** 5 computed summary stat cards, multi-patient monitoring registry table with real-time search & risk filter pills (`ALL`, `HIGH`, `MODERATE`, `LOW`), doctor alert acknowledgment, and floating demo simulator scenario controls.
- **Trend Charts:** Interactive Chart.js graphs for Day, Week, Month, and 3 Months with non-repeating date-time axes.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- `pip` package manager

### 2. Installation & Setup
```bash
# Clone or navigate to project directory
cd smartfoot

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python seed_data.py
```

### 4. Run the Web Server
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

### 5. Run Automated Test Suite
```bash
python verify_system.py
```

---

## 📡 API Reference

### Telemetry Ingestion (ESP32 Hardware / Simulator)
```http
POST /api/v1/telemetry
Header: X-Device-Token: dev-token-sita-101
Content-Type: application/json

{
  "device_token": "dev-token-sita-101",
  "pressure_zones": {
    "L_heel": 34.0, "L_lat_mid": 19.0, "L_med_mid": 17.0, "L_met1": 28.0, "L_met5": 26.0, "L_hallux": 24.0,
    "R_heel": 36.0, "R_lat_mid": 21.0, "R_med_mid": 19.0, "R_met1": 82.0, "R_met5": 30.0, "R_hallux": 52.0
  },
  "temperature_left": 31.8,
  "temperature_right": 34.4,
  "gait_data": { "cadence": 105, "asymmetry": 18.5, "impact_g": 1.4 }
}
```

### Authentication Endpoints
- `POST /auth/request-otp` — Requests 6-digit OTP code for registered email.
- `POST /auth/verify-otp` — Verifies code and creates session.
- `GET /auth/demo-login/<user_id>` — Instant persona login (gated behind `DEMO_MODE=True`).
- `GET /logout` — Signs out current session.

### Clinical & Patient Endpoints
- `GET /patient/dashboard` — Patient dashboard (own data only).
- `GET /patient/api/trends?range=week` — Telemetry history series JSON for Chart.js.
- `GET /doctor/dashboard` — Doctor overview & assigned patient registry.
- `GET /doctor/patient/<id>` — Deep-dive patient telemetry detail view (doctor authorization enforced).
- `POST /api/v1/alerts/<id>/acknowledge` — Doctor alert acknowledgment handler.
- `POST /doctor/api/sim-toggle/<patient_id>` — Toggles demo simulator scenario (`NORMAL`, `MODERATE`, `HIGH_RISK`).

---

## ⚠️ Medical Disclaimer

> *"SmartFoot is a monitoring tool for educational and research purposes. It is not a medical device and has not been validated for clinical use. Do not use for medical diagnosis or treatment decisions. Consult qualified healthcare professionals for medical advice."*

---

## 📌 Known Limitations

- **Sensor Calibration Requirement:** FSR pressure sensors and DS18B20 thermal probes require periodic zero-point calibration for accuracy.
- **Configurable Risk Thresholds:** Risk score thresholds are configurable research parameters and explicitly not clinically validated FDA thresholds.
- **Concurrency Scope:** Single-file SQLite database configuration is designed for research demonstrations; production scale deployment requires PostgreSQL.
- **Regulatory Status:** Not FDA approved. Strictly intended for research, prototype evaluation, and observational demonstration.
- **Demo Mode OTP:** Static OTP code (`123456`) is provided for testing convenience in demo mode and must be swapped with SMTP email delivery prior to production deployment.

---

## 📄 License

This project is released for research, educational, and prototype evaluation purposes.
