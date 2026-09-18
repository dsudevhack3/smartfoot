import sys
import json
import unittest
from datetime import datetime, timezone
from app import create_app
from extensions import db
from models import User, Patient, Doctor, Device, Telemetry, Alert
from risk_engine import RiskEngine
from alert_engine import AlertEngine
from seed_data import seed_database

class SmartfootSystemTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(start_simulators=False)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            seed_database()

    def test_01_risk_engine_determinism(self):
        """Verify Risk Engine deterministic 40/30/30 calculations."""
        with self.app.app_context():
            patient = Patient.query.first()
            zones = dict(patient.baseline_pressure)
            # Add spike on R_met1
            zones['R_met1'] += 50.0

            res1 = RiskEngine.calculate(patient, zones, 31.8, 34.4, {'asymmetry': 18.0})
            res2 = RiskEngine.calculate(patient, zones, 31.8, 34.4, {'asymmetry': 18.0})

            self.assertEqual(res1['score'], res2['score'], "Risk score must be strictly deterministic!")
            self.assertEqual(res1['level'], 'HIGH', "Risk level for 50 kPa spike + 2.6°C temp diff must be HIGH")
            self.assertIn('pressure', res1['factors'])
            self.assertIn('temperature', res1['factors'])
            self.assertIn('gait', res1['factors'])
            print("[OK] Test 01 Passed: Risk Engine calculation determinism verified.")

    def test_02_alert_deduplication(self):
        """Verify alert deduplication (updates existing active alert instead of duplicating rows)."""
        with self.app.app_context():
            patient = Patient.query.first()
            zones = dict(patient.baseline_pressure)
            zones['R_met1'] += 50.0
            
            risk_res = RiskEngine.calculate(patient, zones, 31.8, 34.4, {'asymmetry': 18.0})

            # Run alert engine twice
            alerts1 = AlertEngine.process_telemetry(patient.id, zones, 31.8, 34.4, {'asymmetry': 18.0}, risk_res)
            initial_count = Alert.query.filter_by(patient_id=patient.id, status='ACTIVE').count()

            alerts2 = AlertEngine.process_telemetry(patient.id, zones, 31.8, 34.4, {'asymmetry': 18.0}, risk_res)
            second_count = Alert.query.filter_by(patient_id=patient.id, status='ACTIVE').count()

            self.assertEqual(initial_count, second_count, "De-duplication rule failed: Active alert count increased!")
            
            first_alert = Alert.query.filter_by(patient_id=patient.id, status='ACTIVE').first()
            self.assertNotIn("Automated Hardware Sensor Alert", first_alert.title, "Alert titles must be specific!")
            print(f"[OK] Test 02 Passed: Alert deduplication & specific title verified: '{first_alert.title}'.")

    def test_03_esp32_device_token_ingestion(self):
        """Verify ESP32 hardware API ingestion via device token authentication."""
        with self.app.app_context():
            sita_device = Device.query.filter_by(device_id="ESP32-SITA-01").first()
            token = sita_device.device_token
            sita_patient_id = sita_device.patient_id

        # Valid POST request
        payload = {
            'device_token': token,
            'pressure_zones': {'L_heel': 35.0, 'R_met1': 80.0},
            'temperature_left': 32.0,
            'temperature_right': 34.5,
            'gait_data': {'cadence': 105, 'asymmetry': 12.0}
        }
        res = self.client.post('/api/v1/telemetry', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data['patient_id'], sita_patient_id)

        # Invalid token POST request
        bad_payload = dict(payload, device_token="INVALID_TOKEN_999")
        res_bad = self.client.post('/api/v1/telemetry', data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(res_bad.status_code, 401)
        print("[OK] Test 03 Passed: ESP32 device-token ingestion & isolation routing verified.")

    def test_04_multi_patient_data_isolation(self):
        """Verify multi-patient data isolation across seeded patients."""
        with self.app.app_context():
            patients = Patient.query.all()
            self.assertGreaterEqual(len(patients), 3, "Must seed at least 3 demo patients!")

            scores = []
            for p in patients:
                latest = Telemetry.query.filter_by(patient_id=p.id).order_by(Telemetry.timestamp.desc()).first()
                scores.append(latest.risk_score)

            self.assertEqual(len(set(scores)), len(scores), "Every patient must have distinct telemetry & risk scores!")
            print("[OK] Test 04 Passed: 3+ independent multi-patient streams verified.")

if __name__ == '__main__':
    unittest.main()
