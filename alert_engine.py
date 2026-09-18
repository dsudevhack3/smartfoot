from datetime import datetime, timezone
from extensions import db
from models import Alert

class AlertEngine:
    @staticmethod
    def process_telemetry(patient_id, pressure_zones, temp_left, temp_right, gait_data, risk_result):
        """
        Evaluates incoming telemetry against thresholds and generates/updates de-duplicated alerts.
        """
        alerts_generated = []

        # 1. High Pressure Evaluation
        pressure_factor = risk_result['factors']['pressure']
        if pressure_factor['score'] >= 50.0:
            peak_zone = pressure_factor['peak_zone']
            max_dev = pressure_factor['max_deviation']
            severity = 'CRITICAL' if pressure_factor['score'] >= 75.0 else 'HIGH'
            
            title = f"High Pressure Spike — {peak_zone}"
            desc = f"Localized plantar pressure reached +{max_dev} kPa above baseline at {peak_zone}."
            
            alert = AlertEngine._create_or_update_alert(
                patient_id=patient_id,
                alert_type='HIGH_PRESSURE',
                title=title,
                description=desc,
                severity=severity,
                region=peak_zone,
                deviation_value=max_dev
            )
            if alert:
                alerts_generated.append(alert)

        # 2. Temperature Asymmetry Evaluation
        temp_factor = risk_result['factors']['temperature']
        temp_diff = temp_factor['temp_diff']
        if temp_diff >= 1.5:
            severity = 'CRITICAL' if temp_diff >= 2.5 else ('HIGH' if temp_diff >= 2.0 else 'MEDIUM')
            title = f"Temperature Asymmetry Detected — {temp_diff}°C Δ"
            desc = f"Thermal gradient of {temp_diff}°C between left ({temp_left}°C) and right ({temp_right}°C) foot."
            
            alert = AlertEngine._create_or_update_alert(
                patient_id=patient_id,
                alert_type='TEMP_ASYMMETRY',
                title=title,
                description=desc,
                severity=severity,
                region="Bilateral Feet",
                deviation_value=temp_diff
            )
            if alert:
                alerts_generated.append(alert)

        # 3. Gait Deviation Evaluation
        gait_factor = risk_result['factors']['gait']
        asymmetry = gait_factor['asymmetry']
        if asymmetry >= 15.0:
            severity = 'HIGH' if asymmetry >= 22.0 else 'MEDIUM'
            title = f"Gait Deviation Detected — {asymmetry}% Asymmetry"
            desc = f"IMU stride analysis detected {asymmetry}% asymmetric stance phase duration."
            
            alert = AlertEngine._create_or_update_alert(
                patient_id=patient_id,
                alert_type='GAIT_DEVIATION',
                title=title,
                description=desc,
                severity=severity,
                region="Lower Limb Stride",
                deviation_value=asymmetry
            )
            if alert:
                alerts_generated.append(alert)

        db.session.commit()
        return alerts_generated

    @staticmethod
    def _create_or_update_alert(patient_id, alert_type, title, description, severity, region, deviation_value):
        """
        Enforces De-duplication Rule:
        If an ACTIVE alert exists for the same patient_id, type, and region, update its timestamp
        and description instead of creating a duplicate row.
        """
        existing = Alert.query.filter_by(
            patient_id=patient_id,
            type=alert_type,
            region=region,
            status='ACTIVE'
        ).first()

        if existing:
            # Update existing active alert timestamp and description
            existing.description = description
            existing.severity = severity
            existing.deviation_value = deviation_value
            existing.created_at = datetime.now(timezone.utc)
            return existing
        else:
            # Create new alert
            new_alert = Alert(
                patient_id=patient_id,
                type=alert_type,
                title=title,
                description=description,
                severity=severity,
                region=region,
                deviation_value=deviation_value,
                status='ACTIVE',
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_alert)
            return new_alert
