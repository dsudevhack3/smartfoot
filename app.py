import os
from flask import Flask
from flask_socketio import join_room, leave_room
from config import Config
from extensions import db, login_manager, socketio
from routes.auth import auth_bp
from routes.patient import patient_bp
from routes.doctor import doctor_bp
from routes.api import api_bp
from seed_data import seed_database
from simulator import SimulatorManager
from models import User

def create_app(start_simulators=True):
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(api_bp)

    # SocketIO Event Handlers
    @socketio.on('join_patient_room')
    def handle_join_room(data):
        patient_id = data.get('patient_id')
        if patient_id:
            room_name = f"patient_{patient_id}"
            join_room(room_name)
            print(f"[SocketIO] Client joined isolated room: {room_name}")
            socketio.emit('room_status', {'status': 'connected', 'room': room_name})

    @socketio.on('leave_patient_room')
    def handle_leave_room(data):
        patient_id = data.get('patient_id')
        if patient_id:
            room_name = f"patient_{patient_id}"
            leave_room(room_name)
            print(f"[SocketIO] Client left room: {room_name}")

    # Database & Simulator Setup
    with app.app_context():
        # Create database tables if they do not exist
        db.create_all()
        # If no users exist, run seed_database
        if User.query.count() == 0:
            seed_database()

        # Start background simulator threads if DEMO_MODE is True
        if Config.DEMO_MODE and start_simulators:
            SimulatorManager.start_all(app)

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting SMARTFOOT Tele-monitoring Application on http://127.0.0.1:5000 ...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False, use_reloader=False)
