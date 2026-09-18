from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extensions import db
from models import User, Patient, Doctor

auth_bp = Blueprint('auth', __name__)

def generate_and_send_otp(email):
    """
    Isolated OTP generator function.
    In DEMO_MODE, returns static OTP '123456'.
    Can be swapped to SMTP delivery in one function without changing auth routes.
    """
    otp = Config.STATIC_OTP
    # Store OTP and expiration (5 mins) in session
    session['otp_code'] = otp
    session['otp_email'] = email.lower().strip()
    session['otp_expiry'] = (datetime.now(timezone.utc) + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)).timestamp()
    
    print(f"[Auth] Generated OTP '{otp}' for email: {email}")
    return otp

@auth_bp.route('/')
@auth_bp.route('/login', methods=['GET'])
def login_page():
    if current_user.is_authenticated:
        if current_user.role == 'DOCTOR':
            return redirect(url_for('doctor.dashboard'))
        return redirect(url_for('patient.dashboard'))
    
    # Fetch demo personas for quick selector
    demo_patients = []
    demo_doctors = []
    if Config.DEMO_MODE:
        patients = Patient.query.all()
        for p in patients:
            latest_t = p.telemetries[-1] if p.telemetries else None
            demo_patients.append({
                'user_id': p.user.id,
                'name': p.user.name,
                'patient_code': p.patient_code,
                'risk_score': latest_t.risk_score if latest_t else 20.0,
                'email': p.user.email,
                'photo': p.user.profile_photo_url
            })
        doctors = Doctor.query.all()
        for d in doctors:
            demo_doctors.append({
                'user_id': d.user.id,
                'name': d.user.name,
                'credentials': d.credentials,
                'email': d.user.email,
                'photo': d.user.profile_photo_url
            })

    return render_template(
        'auth/login.html',
        demo_mode=Config.DEMO_MODE,
        demo_otp=Config.STATIC_OTP,
        demo_patients=demo_patients,
        demo_doctors=demo_doctors
    )

@auth_bp.route('/auth/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': False, 'message': 'Email address is required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'Email not registered in SmartFoot database.'}), 404

    otp = generate_and_send_otp(email)
    return jsonify({
        'success': True,
        'message': f'OTP code sent! Demo Mode Code: {otp}'
    })

@auth_bp.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp_entered = data.get('otp', '').strip()

    stored_email = session.get('otp_email')
    stored_otp = session.get('otp_code')
    expiry_ts = session.get('otp_expiry', 0)

    now_ts = datetime.now(timezone.utc).timestamp()

    if not stored_otp or stored_email != email:
        return jsonify({'success': False, 'message': 'No active OTP request found. Please request a new OTP.'}), 400

    if now_ts > expiry_ts:
        return jsonify({'success': False, 'message': 'OTP code has expired. Please request a new code.'}), 400

    if otp_entered != stored_otp:
        return jsonify({'success': False, 'message': 'Invalid OTP code. Try 123456 for demo mode.'}), 400

    # Verification successful
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'User profile not found.'}), 404

    login_user(user, remember=True)

    # Clear OTP session state
    session.pop('otp_code', None)
    session.pop('otp_email', None)
    session.pop('otp_expiry', None)

    redirect_url = url_for('doctor.dashboard') if user.role == 'DOCTOR' else url_for('patient.dashboard')
    return jsonify({
        'success': True,
        'message': 'Authentication successful!',
        'redirect_url': redirect_url
    })

@auth_bp.route('/auth/demo-login/<int:user_id>', methods=['GET'])
def demo_login(user_id):
    if not Config.DEMO_MODE:
        flash("Instant demo login is disabled in production mode.", "danger")
        return redirect(url_for('auth.login_page'))

    user = User.query.get_or_404(user_id)
    login_user(user, remember=True)
    flash(f"Quick-logged in as {user.name} ({user.role})", "success")

    if user.role == 'DOCTOR':
        return redirect(url_for('doctor.dashboard'))
    return redirect(url_for('patient.dashboard'))

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('auth.login_page'))
