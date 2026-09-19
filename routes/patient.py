from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Telemetry, Alert, Patient
from risk_engine import RiskEngine

patient_bp = Blueprint('patient', __name__)

def patient_required(func):
    """Decorator to enforce PATIENT role authorization."""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'PATIENT':
            flash("Access denied. Patient privileges required.", "danger")
            return redirect(url_for('auth.login_page'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@patient_bp.route('/patient/dashboard')
@login_required
@patient_required
def dashboard():
    patient = current_user.patient_profile
    if not patient:
        flash("Patient profile not linked to this user.", "danger")
        return redirect(url_for('auth.login_page'))

    # Fetch latest telemetry record strictly for this patient
    latest_t = Telemetry.query.filter_by(patient_id=patient.id).order_by(Telemetry.timestamp.desc()).first()

    # Calculate current risk & breakdown
    if latest_t:
        p_zones = latest_t.pressure_zones
        tl = latest_t.temperature_left
        tr = latest_t.temperature_right
        gait = latest_t.gait_data
        risk_data = RiskEngine.calculate(patient, p_zones, tl, tr, gait)
    else:
        p_zones = patient.baseline_pressure
        tl = 32.0
        tr = 32.0
        gait = {'cadence': 100, 'asymmetry': 0.0, 'impact_g': 1.1}
        risk_data = RiskEngine.calculate(patient, p_zones, tl, tr, gait)

    # Fetch active alerts for this patient
    active_alerts = Alert.query.filter_by(patient_id=patient.id, status='ACTIVE').order_by(Alert.created_at.desc()).all()

    device_status = patient.device.status if patient.device else 'OFFLINE'

    return render_template(
        'patient/dashboard.html',
        patient=patient,
        latest_telemetry=latest_t,
        pressure_zones=p_zones,
        temp_left=tl,
        temp_right=tr,
        temp_diff=round(abs(tr - float(patient.baseline_temp or 32.2)), 1),
        gait=gait,
        risk_data=risk_data,
        active_alerts=active_alerts,
        device_status=device_status
    )

@patient_bp.route('/patient/api/trends')
@login_required
@patient_required
def trends_api():
    patient = current_user.patient_profile
    time_range = request.args.get('range', 'week').lower()

    now = datetime.now(timezone.utc)
    if time_range == 'day':
        start_time = now - timedelta(days=1)
    elif time_range == 'month':
        start_time = now - timedelta(days=30)
    elif time_range == '3m':
        start_time = now - timedelta(days=90)
    else:  # 'week' default
        start_time = now - timedelta(days=7)

    # Scoped query: strictly WHERE patient_id = :id
    records = Telemetry.query.filter(
        Telemetry.patient_id == patient.id,
        Telemetry.timestamp >= start_time
    ).order_by(Telemetry.timestamp.asc()).all()

    timestamps = []
    temp_diffs = []
    peak_pressures = []
    gait_asymmetries = []
    risk_scores = []

    for r in records:
        # Distinct, human-readable timestamp string
        timestamps.append(r.timestamp.strftime('%b %d, %H:%M'))
        temp_diffs.append(round(abs(r.temperature_right - float(patient.baseline_temp or 32.2)), 1))
        
        # Max pressure across 12 zones
        zones = r.pressure_zones
        max_p = max(zones.values()) if zones else 30.0
        peak_pressures.append(round(max_p, 1))
        
        asym = r.gait_data.get('asymmetry', 0.0) if r.gait_data else 0.0
        gait_asymmetries.append(round(asym, 1))
        risk_scores.append(round(r.risk_score, 1))

    return jsonify({
        'success': True,
        'patient_id': patient.id,
        'range': time_range,
        'labels': timestamps,
        'temp_diffs': temp_diffs,
        'peak_pressures': peak_pressures,
        'gait_asymmetries': gait_asymmetries,
        'risk_scores': risk_scores
    })

@patient_bp.route('/patient/settings')
@login_required
@patient_required
def settings():
    patient = current_user.patient_profile
    return render_template('patient/settings.html', patient=patient)
