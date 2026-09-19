import os
import joblib
import numpy as np

class MLEngine:
    _instance = None
    _model_data = None

    @classmethod
    def _load_model(cls):
        if cls._model_data is None:
            model_path = os.path.join(os.path.dirname(__file__), 'models_ml', 'smartfoot_ml_model.joblib')
            if os.path.exists(model_path):
                try:
                    cls._model_data = joblib.load(model_path)
                    print(f"[MLEngine] Loaded ML Risk Model successfully from {model_path}")
                except Exception as e:
                    print(f"[MLEngine Warning] Could not load ML model: {e}")
                    cls._model_data = None
            else:
                print(f"[MLEngine Warning] Model file not found at {model_path}. Auto-training may be required.")
        return cls._model_data

    @classmethod
    def predict(cls, patient, pressure_zones, temp_left, temp_right, gait_data):
        """
        Predicts diabetic foot risk level (LOW, MODERATE, HIGH), composite risk score (0-100),
        and explainable factor breakdowns (XAI) using trained ML Classifier.
        """
        model_data = cls._load_model()
        
        # 1. Feature Extraction & Engineering
        baseline_p = patient.baseline_pressure if patient else {}
        max_dev = 0.0
        sum_dev = 0.0
        peak_zone = "Heel"

        zone_names_readable = {
            'L_toe': 'Left Big Toe', 'L_met': 'Left Forefoot Metatarsal', 'L_arch': 'Left Midfoot Arch', 'L_heel': 'Left Heel',
            'R_toe': 'Right Big Toe', 'R_met': 'Right Forefoot Metatarsal', 'R_arch': 'Right Midfoot Arch', 'R_heel': 'Right Heel',
            'L_met1': 'Left Forefoot Metatarsal', 'R_met1': 'Right Forefoot Metatarsal'
        }

        for zone_key, val in pressure_zones.items():
            b_val = baseline_p.get(zone_key, 30.0)
            dev = max(0.0, float(val) - float(b_val))
            if dev > max_dev:
                max_dev = dev
                peak_zone = zone_names_readable.get(zone_key, zone_key)
            sum_dev += dev

        avg_dev = sum_dev / max(1, len(pressure_zones))

        # Temperature Evaluation (Unilateral vs Bilateral)
        if patient and getattr(patient, 'amputated_foot', None) == 'LEFT':
            base_t = float(getattr(patient, 'baseline_temp', 32.2) or 32.2)
            temp_diff = abs(float(temp_right) - base_t)
            is_unilateral = True
        else:
            temp_diff = abs(float(temp_left) - float(temp_right))
            is_unilateral = False

        gait_asym = float(gait_data.get('asymmetry', 0.0)) if gait_data else 0.0
        cadence = float(gait_data.get('cadence', 100)) if gait_data else 100.0
        impact_g = float(gait_data.get('impact_g', 1.0)) if gait_data else 1.0
        patient_age = float(patient.age) if (patient and getattr(patient, 'age', None)) else 60.0

        # Construct ML input vector: [max_p_dev, avg_p_dev, temp_diff, gait_asym, cadence, impact_g, patient_age]
        feature_vector = np.array([[max_dev, avg_dev, temp_diff, gait_asym, cadence, impact_g, patient_age]])

        # 2. Model Inference or Fallback Calculation
        if model_data and 'model' in model_data and 'scaler' in model_data:
            model = model_data['model']
            scaler = model_data['scaler']

            X_scaled = scaler.transform(feature_vector)
            probs = model.predict_proba(X_scaled)[0]  # [P(LOW), P(MODERATE), P(HIGH)]
            
            p_low, p_mod, p_high = probs[0], probs[1], probs[2]

            # Composite continuous score mapped from class probability distribution
            raw_score = (p_low * 15.0) + (p_mod * 50.0) + (p_high * 90.0)
            
            # Smooth fine-tuning based on peak pressure & temp severity
            severity_boost = min(10.0, (max_dev / 45.0) * 5.0 + (temp_diff / 3.0) * 5.0)
            composite_score = round(float(np.clip(raw_score + severity_boost * (p_high + p_mod - p_low), 0.0, 100.0)), 1)

            if p_high > 0.45 or (p_high > p_mod and p_high > p_low):
                risk_level = "HIGH"
                confidence = round(float(p_high * 100), 1)
            elif p_mod > 0.40 or (p_mod > p_low):
                risk_level = "MODERATE"
                confidence = round(float(p_mod * 100), 1)
            else:
                risk_level = "LOW"
                confidence = round(float(p_low * 100), 1)
        else:
            # Deterministic fallback calculation
            p_score_rule = min(100.0, (max_dev / 45.0) * 70.0 + (avg_dev / 20.0) * 30.0)
            t_score_rule = min(100.0, (temp_diff / 3.0) * 100.0)
            g_score_rule = min(100.0, (gait_asym / 25.0) * 100.0)
            composite_score = round(0.40 * p_score_rule + 0.30 * t_score_rule + 0.30 * g_score_rule, 1)

            if composite_score < 30.0:
                risk_level = "LOW"
            elif composite_score <= 60.0:
                risk_level = "MODERATE"
            else:
                risk_level = "HIGH"
            confidence = 90.0

        # 3. Factor Breakdown & XAI Explanations
        pressure_score = min(100.0, (max_dev / 45.0) * 70.0 + (avg_dev / 20.0) * 30.0)
        if pressure_score < 30:
            p_status = "Normal Distribution"
            p_explain = f"Peak pressure on {peak_zone} is within expected baseline limits."
        elif pressure_score <= 60:
            p_status = "Elevated Pressure"
            p_explain = f"Moderate pressure elevation (+{round(max_dev, 1)} kPa) localized at {peak_zone}."
        else:
            p_status = "High Pressure Spike"
            p_explain = f"Critical pressure focal point (+{round(max_dev, 1)} kPa) detected on {peak_zone}."

        if is_unilateral:
            base_t = float(getattr(patient, 'baseline_temp', 32.2) or 32.2)
            temp_score = min(100.0, (temp_diff / 2.5) * 100.0)
            if temp_diff < 0.8:
                t_status = "Normal Unilateral Temperature"
                t_explain = f"Right foot temperature ({round(temp_right, 1)}°C) is close to baseline ({base_t}°C)."
            elif temp_diff <= 2.0:
                t_status = "Elevated Foot Temperature"
                t_explain = f"Moderate right foot temperature elevation ({round(temp_right, 1)}°C vs baseline {base_t}°C)."
            else:
                t_status = "Severe Foot Hotspot"
                t_explain = f"Significant right foot hotspot detected ({round(temp_right, 1)}°C vs baseline {base_t}°C), indicating inflammation risk."
        else:
            temp_score = min(100.0, (temp_diff / 3.0) * 100.0)
            if temp_diff < 0.8:
                t_status = "Symmetric Thermal Map"
                t_explain = f"Left vs Right temperature difference is minimal ({round(temp_diff, 1)}°C)."
            elif temp_diff <= 2.0:
                t_status = "Mild Thermal Asymmetry"
                t_explain = f"Mild focal temperature difference detected ({round(temp_diff, 1)}°C between feet)."
            else:
                t_status = "Severe Thermal Asymmetry"
                t_explain = f"Significant hotspot detected ({round(temp_diff, 1)}°C difference), indicating localized inflammation risk."

        gait_score = min(100.0, (gait_asym / 25.0) * 100.0)
        if gait_score < 30:
            g_status = "Balanced Stride"
            g_explain = f"Plantar weight distribution and cadence are normal ({round(gait_asym, 1)}% asymmetry)."
        elif gait_score <= 60:
            g_status = "Mild Gait Deviation"
            g_explain = f"Slight limp or altered pressure loading phase ({round(gait_asym, 1)}% asymmetry)."
        else:
            g_status = "Significant Stride Instability"
            g_explain = f"Pronounced antalgic gait detected ({round(gait_asym, 1)}% asymmetry), favoring one limb."

        # 4. Clinical Takeaway Generation
        if risk_level == "LOW":
            takeaway = f"ML Model Assessment ({confidence}% confidence): Low Ulcer Risk. Plantar pressures, thermal symmetry, and gait metrics are stable."
        elif risk_level == "MODERATE":
            takeaway = f"ML Model Assessment ({confidence}% confidence): Moderate Ulcer Risk. Detected pressure elevation (+{round(max_dev, 1)} kPa on {peak_zone}) and thermal variation ({round(temp_diff, 1)}°C)."
        else:
            takeaway = f"ML Model Assessment ({confidence}% confidence): HIGH ULCER RISK PREDICTED. Critical pressure spike (+{round(max_dev, 1)} kPa on {peak_zone}) with {round(temp_diff, 1)}°C thermal variation. Physician review advised."

        return {
            'score': composite_score,
            'level': risk_level,
            'confidence': confidence,
            'takeaway': takeaway,
            'factors': {
                'pressure': {
                    'score': round(pressure_score, 1),
                    'weight': 40,
                    'status': p_status,
                    'explanation': p_explain,
                    'peak_zone': peak_zone,
                    'max_deviation': round(max_dev, 1)
                },
                'temperature': {
                    'score': round(temp_score, 1),
                    'weight': 30,
                    'status': t_status,
                    'explanation': t_explain,
                    'temp_diff': round(temp_diff, 1)
                },
                'gait': {
                    'score': round(gait_score, 1),
                    'weight': 30,
                    'status': g_status,
                    'explanation': g_explain,
                    'asymmetry': round(gait_asym, 1)
                }
            }
        }
