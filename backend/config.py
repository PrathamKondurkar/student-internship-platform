import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "student_internship_platform")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "instance/reporting.db")
    ALLOW_ADMIN_REGISTRATION = os.getenv("ALLOW_ADMIN_REGISTRATION", "false").lower() == "true"
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
