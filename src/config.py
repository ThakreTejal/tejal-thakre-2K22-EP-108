import os
from pathlib import Path

basedir = Path(__file__).parent.parent
database_path = basedir / "boostly.db"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

