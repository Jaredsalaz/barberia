from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Balam SaaS"
    API_V1_STR: str = "/api/v1"
    
    # Base de Datos
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS: Optional[str] = None

    # PayPal Configuration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"

    # Email Configuration (GMAIL SMTP)
    GMAIL_USER: Optional[str] = None
    GMAIL_PASSWORD: Optional[str] = None

    # DeepSeek API
    DEEPSEEK_API_KEY: str

    # NVIDIA API
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Seguridad
    SECRET_KEY: str = "balam_barber_secret_key_production_2024_stable"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 semana

    # OpenWA Gateway Configuration
    OPENWA_API_URL: str = "http://localhost:2785/api"
    OPENWA_API_KEY: str = "dev-admin-key"
    OPENWA_SESSION_ID: str = "balam-session"
    OPENWA_SESSION_UUID: str = ""
    WHATSAPP_WEBHOOK_URL: str = "http://localhost:8000/api/v1/webhook/whatsapp"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
