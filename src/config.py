import os
import secrets

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "airline_cascades")
    # Signs the session cookie (flash messages, CSRF token). Set it in production;
    # the fallback is random per process, so sessions end on restart.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
