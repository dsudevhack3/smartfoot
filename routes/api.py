from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from extensions import db, socketio
from models import Device, Telemetry, Patient
from risk_engine import RiskEngine
from alert_engine import AlertEngine

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/v1/telemetry', methods=['POST'])
def receive_telemetry():
    """
    ESP32 hardware telemetry POST endpoint.
    Requires device-token authentication via header or payload.
    Maps device_token -> patient_id for end-to-end multi-patient data isolation.
    """
    data = request.get_json() or {}
    device_token = request.headers.get('X-Device-Token') or data.get('device_token')

    if not device_token:
        return jsonify({'error': 'Unauthorized: Missing device_token header or parameter.'}), 401

    # Lookup device & resolve patient_id
    device = Device.query.filter_by(device_token=device_token).first()
    if not device:
        return jsonify({'error': 'Unauthorized: Invalid or unknown device_token.'}), 401

    patient = device.patient
    if not patient:
        return jsonify({'error': 'Configuration Error: Device is not mapped to any active patient.'}), 400

    # Parse payload inputs
    pressure_zones = data.get('pressure_zones', {})
    temp_left = float(data.get('temperature_left', 32.0))
    temp_right = float(data.get('temperature_right', 32.0))
    gait_data = data.get('gait_data', {'cadence': 100, 'asymmetry': 0.0, 'impact_g': 1.0})
    is_sim = bool(data.get('is_simulated', False))

    # Basic input sanity validation
    if not isinstance(pressure_zones, dict) or len(pressure_zones) == 0:
        return jsonify({'error': 'Invalid payload: pressure_zones dictionary required.'}), 400

    # Execute Risk Calculation & Alert Engines
    risk_res = RiskEngine.calculate(patient, pressure_zones, temp_left, temp_right, gait_data)
    alerts = AlertEngine.process_telemetry(patient.id, pressure_zones, temp_left, temp_right, gait_data, risk_res)

    # Save Telemetry row
    tele = Telemetry(
        patient_id=patient.id,
        timestamp=datetime.now(timezone.utc),
        pressure_zones=pressure_zones,
        temperature_left=temp_left,
        temperature_right=temp_right,
        gait_data=gait_data,
        risk_score=risk_res['score'],
        is_simulated=is_sim
    )
    db.session.add(tele)

    # Update Device last_seen status
    device.status = 'ONLINE'
    device.last_seen_at = datetime.now(timezone.utc)
    db.session.commit()

    # Emit SocketIO broadcast strictly to room `patient_{id}`
    payload = {
        'patient_id': patient.id,
        'timestamp': tele.timestamp.strftime('%H:%M:%S'),
        'pressure_zones': pressure_zones,
        'temperature_left': temp_left,
        'temperature_right': temp_right,
        'temp_diff': round(abs(temp_left - temp_right), 1),
        'gait_data': gait_data,
        'risk_score': risk_res['score'],
        'risk_level': risk_res['level'],
        'risk_takeaway': risk_res['takeaway'],
        'risk_factors': risk_res['factors'],
        'active_alerts_count': len(alerts)
    }
    socketio.emit('telemetry_update', payload, to=f"patient_{patient.id}")

    return jsonify({
        'status': 'success',
        'patient_id': patient.id,
        'risk_score': risk_res['score'],
        'risk_level': risk_res['level'],
        'alerts_triggered': len(alerts)
    }), 201


@api_bp.route('/api/v1/health', methods=['GET'])
def health_check():
    """Service health monitoring endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'SMARTFOOT Tele-monitoring Engine',
        'version': '3.0-PROTOTYPE',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
