import os
from datetime import timedelta

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'jobs.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = 'your-secret-key-here-change-in-production'
    SECURITY_PASSWORD_SALT = 'your-password-salt-change-in-production'

    PASSWORD_EXPIRY_DAYS = 30
    PASSWORD_HISTORY_COUNT = 1

    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'rtf'}

    PROFILE_COMPLETION_PERCENTAGE = 100
    PHOTO_BOOST_PERCENTAGE = 40

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME_MINUTES = 15

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'
    MAIL_PASSWORD = 'your-app-password'

    # Dev default OTP (for testing): set to 6-digit string or None for random OTP
    DEV_DEFAULT_OTP = '123456'
