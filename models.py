from datetime import datetime, timezone
import json
from flask_login import UserMixin
from extensions import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'PATIENT' or 'DOCTOR'
    profile_photo_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    patient_profile = db.relationship('Patient', backref='user', uselist=False, cascade="all, delete-orphan")
    doctor_profile = db.relationship('Doctor', backref='user', uselist=False, cascade="all, delete-orphan")

    def __init__(self, email=None, name=None, role=None, profile_photo_url=None, created_at=None, **kwargs):
        super().__init__(**kwargs)
        if email is not None: self.email = email
        if name is not None: self.name = name
        if role is not None: self.role = role
        if profile_photo_url is not None: self.profile_photo_url = profile_photo_url
        if created_at is not None: self.created_at = created_at

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    credentials = db.Column(db.String(100), default='MD, Podiatrist')
    specialty = db.Column(db.String(100), default='Diabetic Foot Specialist')

    # Relationships
    patients = db.relationship('Patient', backref='assigned_doctor', lazy=True)

    def __init__(self, user_id=None, credentials='MD, Podiatrist', specialty='Diabetic Foot Specialist', **kwargs):
        super().__init__(**kwargs)
        if user_id is not None: self.user_id = user_id
        if credentials is not None: self.credentials = credentials
        if specialty is not None: self.specialty = specialty

    def __repr__(self):
        return f'<Doctor Dr. {self.user.name if self.user else self.id}>'


class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    patient_code = db.Column(db.String(30), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    
    # Baselines & Clinical Profile
    amputated_foot = db.Column(db.String(10), nullable=True)  # 'LEFT', 'RIGHT', or None
    baseline_pressure_json = db.Column(db.Text, nullable=True)  # JSON string of zones baseline (kPa)
    baseline_temp = db.Column(db.Float, default=32.5)  # Baseline foot temperature (°C)
    baseline_gait = db.Column(db.Float, default=95.0)  # Baseline gait symmetry %

    # Relationships
    device = db.relationship('Device', backref='patient', uselist=False, cascade="all, delete-orphan")
    telemetries = db.relationship('Telemetry', backref='patient', lazy=True, cascade="all, delete-orphan")
    alerts = db.relationship('Alert', backref='patient', lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id=None, patient_code=None, age=None, gender=None, assigned_doctor_id=None, baseline_pressure=None, baseline_temp=32.5, baseline_gait=95.0, amputated_foot=None, **kwargs):
        super().__init__(**kwargs)
        if user_id is not None: self.user_id = user_id
        if patient_code is not None: self.patient_code = patient_code
        if age is not None: self.age = age
        if gender is not None: self.gender = gender
        if assigned_doctor_id is not None: self.assigned_doctor_id = assigned_doctor_id
        if baseline_pressure is not None: self.baseline_pressure = baseline_pressure
        if baseline_temp is not None: self.baseline_temp = baseline_temp
        if baseline_gait is not None: self.baseline_gait = baseline_gait
        if amputated_foot is not None: self.amputated_foot = amputated_foot

    @property
    def baseline_pressure(self):
        if self.baseline_pressure_json:
            try:
                return json.loads(self.baseline_pressure_json)
            except Exception:
                pass
        # Default baseline across 12 zones (6 left, 6 right) in kPa
        return {
            'L_heel': 35.0, 'L_lat_mid': 20.0, 'L_med_mid': 18.0, 'L_met1': 30.0, 'L_met5': 28.0, 'L_hallux': 25.0,
            'R_heel': 35.0, 'R_lat_mid': 20.0, 'R_med_mid': 18.0, 'R_met1': 30.0, 'R_met5': 28.0, 'R_hallux': 25.0
        }

    @baseline_pressure.setter
    def baseline_pressure(self, value):
        self.baseline_pressure_json = json.dumps(value)

    def __repr__(self):
        return f'<Patient {self.patient_code} ({self.user.name if self.user else self.id})>'


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)
    device_token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, unique=True)
    status = db.Column(db.String(20), default='ONLINE')  # 'ONLINE' or 'OFFLINE'
    last_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, device_id=None, device_token=None, patient_id=None, status='ONLINE', last_seen_at=None, **kwargs):
        super().__init__(**kwargs)
        if device_id is not None: self.device_id = device_id
        if device_token is not None: self.device_token = device_token
        if patient_id is not None: self.patient_id = patient_id
        if status is not None: self.status = status
        if last_seen_at is not None: self.last_seen_at = last_seen_at

    def __repr__(self):
        return f'<Device {self.device_id} -> Patient {self.patient_id}>'


class Telemetry(db.Model):
    __tablename__ = 'telemetry'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # 12 bilateral zones pressure values in kPa (JSON)
    pressure_zones_json = db.Column(db.Text, nullable=False)
    
    # Temperatures (°C)
    temperature_left = db.Column(db.Float, nullable=False)
    temperature_right = db.Column(db.Float, nullable=False)
    
    # IMU / Gait metrics (JSON: cadence, asymmetry, impact)
    gait_data_json = db.Column(db.Text, nullable=False)
    
    risk_score = db.Column(db.Float, nullable=False, default=0.0)
    is_simulated = db.Column(db.Boolean, default=True)

    def __init__(self, patient_id=None, timestamp=None, pressure_zones=None, temperature_left=32.0, temperature_right=32.0, gait_data=None, risk_score=0.0, is_simulated=True, **kwargs):
        super().__init__(**kwargs)
        if patient_id is not None: self.patient_id = patient_id
        if timestamp is not None: self.timestamp = timestamp
        if pressure_zones is not None: self.pressure_zones = pressure_zones
        if temperature_left is not None: self.temperature_left = temperature_left
        if temperature_right is not None: self.temperature_right = temperature_right
        if gait_data is not None: self.gait_data = gait_data
        if risk_score is not None: self.risk_score = risk_score
        if is_simulated is not None: self.is_simulated = is_simulated

    @property
    def pressure_zones(self):
        return json.loads(self.pressure_zones_json) if self.pressure_zones_json else {}

    @pressure_zones.setter
    def pressure_zones(self, value):
        self.pressure_zones_json = json.dumps(value)

    @property
    def gait_data(self):
        return json.loads(self.gait_data_json) if self.gait_data_json else {}

    @gait_data.setter
    def gait_data(self, value):
        self.gait_data_json = json.dumps(value)

    def __repr__(self):
        return f'<Telemetry Patient {self.patient_id} @ {self.timestamp} Risk={self.risk_score}>'


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # 'HIGH_PRESSURE', 'TEMP_ASYMMETRY', 'GAIT_DEVIATION', 'SENSOR_DISCONNECTED'
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    region = db.Column(db.String(50), nullable=True)  # e.g., "Right Forefoot", "Left Heel"
    baseline_value = db.Column(db.Float, nullable=True)
    deviation_value = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE', index=True)  # 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)

    def __init__(self, patient_id=None, type=None, title=None, description=None, severity=None, region=None, baseline_value=None, deviation_value=None, status='ACTIVE', created_at=None, acknowledged_by=None, **kwargs):
        super().__init__(**kwargs)
        if patient_id is not None: self.patient_id = patient_id
        if type is not None: self.type = type
        if title is not None: self.title = title
        if description is not None: self.description = description
        if severity is not None: self.severity = severity
        if region is not None: self.region = region
        if baseline_value is not None: self.baseline_value = baseline_value
        if deviation_value is not None: self.deviation_value = deviation_value
        if status is not None: self.status = status
        if created_at is not None: self.created_at = created_at
        if acknowledged_by is not None: self.acknowledged_by = acknowledged_by

    def __repr__(self):
        return f'<Alert {self.type} ({self.severity}) for Patient {self.patient_id}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
