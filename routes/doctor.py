from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from config import Config
from extensions import db
from models import Patient, Doctor, Telemetry, Alert
from risk_engine import RiskEngine
from simulator import SimulatorManager

doctor_bp = Blueprint('doctor', __name__)

def doctor_required(func):
    """Decorator to enforce DOCTOR role authorization."""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'DOCTOR':
            flash("Access denied. Doctor privileges required.", "danger")
            return redirect(url_for('auth.login_page'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@doctor_bp.route('/doctor/dashboard')
@login_required
@doctor_required
def dashboard():
    doctor = current_user.doctor_profile
    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for('auth.login_page'))

    # Fetch patients assigned strictly to this doctor
    assigned_patients = Patient.query.filter_by(assigned_doctor_id=doctor.id).all()

    # Calculate 5 Summary Stats across assigned patients
    total_patients = len(assigned_patients)
    low_risk_count = 0
    mod_risk_count = 0
    high_risk_count = 0
    total_active_alerts = 0

    patient_rows = []

    for p in assigned_patients:
        # Latest telemetry strictly for patient p
        latest_t = Telemetry.query.filter_by(patient_id=p.id).order_by(Telemetry.timestamp.desc()).first()
        active_alerts = Alert.query.filter_by(patient_id=p.id, status='ACTIVE').all()

        alert_count = len(active_alerts)
        total_active_alerts += alert_count

        if latest_t:
            r_score = latest_t.risk_score
            p_zones = latest_t.pressure_zones
            peak_p = max(p_zones.values()) if p_zones else 30.0
            t_diff = round(abs(latest_t.temperature_left - latest_t.temperature_right), 1)
            asym = latest_t.gait_data.get('asymmetry', 0.0) if latest_t.gait_data else 0.0
            gait_sym = round(max(0.0, 100.0 - asym), 1)
            last_seen = latest_t.timestamp.strftime('%H:%M:%S')
        else:
            r_score = 15.0
            peak_p = 32.0
            t_diff = 0.3
            gait_sym = 98.0
            last_seen = "N/A"

        # Risk level classification
        if r_score > 60.0:
            r_level = 'HIGH'
            high_risk_count += 1
        elif r_score >= 30.0:
            r_level = 'MODERATE'
            mod_risk_count += 1
        else:
            r_level = 'LOW'
            low_risk_count += 1

        patient_rows.append({
            'patient': p,
            'user': p.user,
            'risk_score': round(r_score, 1),
            'risk_level': r_level,
            'peak_pressure': round(peak_p, 1),
            'temp_diff': t_diff,
            'gait_symmetry': gait_sym,
            'active_alerts_count': alert_count,
            'device_status': p.device.status if p.device else 'OFFLINE',
            'last_updated': last_seen
        })

    return render_template(
        'doctor/dashboard.html',
        doctor=doctor,
        stats={
            'total_patients': total_patients,
            'low_risk': low_risk_count,
            'mod_risk': mod_risk_count,
            'high_risk': high_risk_count,
            'active_alerts': total_active_alerts
        },
        patient_rows=patient_rows,
        demo_mode=Config.DEMO_MODE
    )

@doctor_bp.route('/doctor/patient/<int:patient_id>')
@login_required
@doctor_required
def patient_detail(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)

    # Scoped authorization check: Doctor can only access assigned patients
    if patient.assigned_doctor_id != doctor.id:
        flash("Unauthorized: You are not assigned to this patient.", "danger")
        return redirect(url_for('doctor.dashboard'))

    latest_t = Telemetry.query.filter_by(patient_id=patient.id).order_by(Telemetry.timestamp.desc()).first()
    active_alerts = Alert.query.filter_by(patient_id=patient.id).order_by(Alert.created_at.desc()).all()

    if latest_t:
        p_zones = latest_t.pressure_zones
        tl = latest_t.temperature_left
        tr = latest_t.temperature_right
        gait = latest_t.gait_data
        risk_data = RiskEngine.calculate(patient, p_zones, tl, tr, gait)
    else:
        p_zones = patient.baseline_pressure
        tl, tr = 32.0, 32.0
        gait = {'cadence': 100, 'asymmetry': 0.0, 'impact_g': 1.1}
        risk_data = RiskEngine.calculate(patient, p_zones, tl, tr, gait)

    return render_template(
        'doctor/patient_detail.html',
        doctor=doctor,
        patient=patient,
        latest_telemetry=latest_t,
        pressure_zones=p_zones,
        temp_left=tl,
        temp_right=tr,
        temp_diff=round(abs(tl - tr), 1),
        gait=gait,
        risk_data=risk_data,
        alerts=active_alerts,
        demo_mode=Config.DEMO_MODE
    )

@doctor_bp.route('/api/v1/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
@doctor_required
def acknowledge_alert(alert_id):
    doctor = current_user.doctor_profile
    alert = Alert.query.get_or_404(alert_id)

    # Scoped check: only allow acknowledging alerts for assigned patients
    if alert.patient.assigned_doctor_id != doctor.id:
        return jsonify({'success': False, 'message': 'Unauthorized to acknowledge alert for this patient.'}), 403

    alert.status = 'ACKNOWLEDGED'
    alert.acknowledged_by = doctor.id
    db.session.commit()

    return jsonify({
        'success': True,
        'alert_id': alert.id,
        'status': 'ACKNOWLEDGED',
        'message': f'Alert "{alert.title}" acknowledged by Dr. {doctor.user.name}.'
    })

@doctor_bp.route('/doctor/api/sim-toggle/<int:patient_id>', methods=['POST'])
@login_required
@doctor_required
def toggle_simulator(patient_id):
    if not Config.DEMO_MODE:
        return jsonify({'success': False, 'message': 'Demo mode disabled.'}), 400

    data = request.get_json() or {}
    scenario = data.get('scenario', 'DEFAULT').upper()

    success = SimulatorManager.set_patient_scenario(patient_id, scenario)
    if success:
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'scenario': scenario,
            'message': f'Patient #{patient_id} simulator toggled to {scenario}.'
        })
    return jsonify({'success': False, 'message': 'Simulator instance not active.'}), 404
