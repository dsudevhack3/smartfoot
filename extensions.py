from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

login_manager.login_view = 'auth.login_page'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
