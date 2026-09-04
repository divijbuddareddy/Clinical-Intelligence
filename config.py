import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clinical-workflow-intel-secret-key-2026")
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'clinical_platform.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File storage configuration
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    VECTOR_STORE_FOLDER = BASE_DIR / "vector_store"
    EXPORT_FOLDER = BASE_DIR / "exports"
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB max file size
    ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "md"}
    
    # Gemini & AI configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    EMBEDDING_DIMENSION = 384  # Standard dense vector dimension
    TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "4"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "450"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
    
    # Security & Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

# Ensure runtime directories exist
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
Config.VECTOR_STORE_FOLDER.mkdir(parents=True, exist_ok=True)
Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
