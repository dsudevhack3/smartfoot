import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartfoot-secret-key-healthcare-demo-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///smartfoot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Demo & Authentication Settings
    DEMO_MODE = os.environ.get('DEMO_MODE', 'True').lower() in ('true', '1', 't')
    STATIC_OTP = "123456"
    OTP_EXPIRY_MINUTES = 5
    
    # WebSocket Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartfoot-secret-key-healthcare-demo-2026')
