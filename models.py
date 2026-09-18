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
    
    # Baselines for deviation calculations
    baseline_pressure_json = db.Column(db.Text, nullable=True)  # JSON string of 12 zones baseline (kPa)
    baseline_temp = db.Column(db.Float, default=32.5)  # Baseline foot temperature (°C)
    baseline_gait = db.Column(db.Float, default=95.0)  # Baseline gait symmetry %

    # Relationships
    device = db.relationship('Device', backref='patient', uselist=False, cascade="all, delete-orphan")
    telemetries = db.relationship('Telemetry', backref='patient', lazy=True, cascade="all, delete-orphan")
    alerts = db.relationship('Alert', backref='patient', lazy=True, cascade="all, delete-orphan")

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

    def __repr__(self):
        return f'<Alert {self.type} ({self.severity}) for Patient {self.patient_id}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
