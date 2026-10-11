import os
from dotenv import load_dotenv

load_dotenv()


BRAND_NAME = "Marketora"
ORDER_PREFIX = "MR"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY","dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///market_hub.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Keeps stale pooled connections from breaking requests
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True

    # Product image uploads (up to 8 images x 5 MB per request)
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024
