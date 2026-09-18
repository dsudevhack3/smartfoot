class RiskEngine:
    @staticmethod
    def calculate(patient, pressure_zones, temp_left, temp_right, gait_data):
        """
        Calculates a deterministic 0-100 risk score and factor breakdown per Section 9.
        Weights: 40% Pressure Deviation, 30% Temp Asymmetry, 30% Gait Deviation.
        """
        baseline_p = patient.baseline_pressure if patient else {}
        
        # 1. Pressure Deviation (40% Weight)
        max_dev = 0.0
        sum_dev = 0.0
        peak_zone = "Heel"
        
        zone_names_readable = {
            'L_heel': 'Left Heel', 'L_lat_mid': 'Left Lateral Midfoot', 'L_med_mid': 'Left Medial Midfoot',
            'L_met1': 'Left 1st Metatarsal', 'L_met5': 'Left 5th Metatarsal', 'L_hallux': 'Left Big Toe',
            'R_heel': 'Right Heel', 'R_lat_mid': 'Right Lateral Midfoot', 'R_med_mid': 'Right Medial Midfoot',
            'R_met1': 'Right 1st Metatarsal', 'R_met5': 'Right 5th Metatarsal', 'R_hallux': 'Right Big Toe'
        }

        for zone_key, val in pressure_zones.items():
            b_val = baseline_p.get(zone_key, 30.0)
            dev = max(0.0, float(val) - float(b_val))
            if dev > max_dev:
                max_dev = dev
                peak_zone = zone_names_readable.get(zone_key, zone_key)
            sum_dev += dev
        
        avg_dev = sum_dev / max(1, len(pressure_zones))
        # Max deviation of 45+ kPa over baseline = 100% score for pressure component
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

        # 2. Temperature Asymmetry (30% Weight)
        temp_diff = abs(float(temp_left) - float(temp_right))
        # 3.0°C difference = 100% score for temperature component
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

        # 3. Gait Deviation (30% Weight)
        asymmetry = float(gait_data.get('asymmetry', 0.0))
        # 25% asymmetry = 100% score for gait component
        gait_score = min(100.0, (asymmetry / 25.0) * 100.0)
        
        if gait_score < 30:
            g_status = "Balanced Stride"
            g_explain = f"Plantar weight distribution and cadence are normal ({round(asymmetry, 1)}% asymmetry)."
        elif gait_score <= 60:
            g_status = "Mild Gait Deviation"
            g_explain = f"Slight limp or altered pressure loading phase ({round(asymmetry, 1)}% asymmetry)."
        else:
            g_status = "Significant Stride Instability"
            g_explain = f"Pronounced antalgic gait detected ({round(asymmetry, 1)}% asymmetry), favoring one limb."

        # 4. Total Composite Risk Score (Weighted 40 / 30 / 30)
        composite_score = round(0.40 * pressure_score + 0.30 * temp_score + 0.30 * gait_score, 1)
        
        if composite_score < 30.0:
            risk_level = "LOW"
            takeaway = f"Low overall risk: Baseline metrics healthy. Continue normal daily routine and check insoles daily."
        elif composite_score <= 60.0:
            risk_level = "MODERATE"
            takeaway = f"Moderate risk: Elevated {peak_zone.lower()} pressure and thermal variation. Re-examine foot skin and schedule a 3-day recheck."
        else:
            risk_level = "HIGH"
            takeaway = f"High risk: Critical pressure focal spike on {peak_zone} with {round(temp_diff, 1)}°C temperature asymmetry. Consult your physician promptly."

        return {
            'score': composite_score,
            'level': risk_level,
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
                    'asymmetry': round(asymmetry, 1)
                }
            }
        }
