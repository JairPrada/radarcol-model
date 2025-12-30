"""
Configuración de la aplicación y variables de entorno.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

# =====================================
# Configuración del Servidor
# =====================================
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# =====================================
# Configuración de la API Externa
# =====================================
BASE_URL = os.getenv("BASE_URL", "https://www.datos.gov.co/resource/jbjy-vk9h.json")

# =====================================
# Configuración del Motor de Análisis
# =====================================
# API Key para Groq (LLM gratuito - https://console.groq.com/keys)
# Free tier: 30 requests/minuto, 14,400 requests/día
GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
RUTA_ARTEFACTOS = os.getenv("RUTA_ARTEFACTOS", "data/artifacts")

# =====================================
# Configuración CORS
# =====================================
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "")

if CORS_ORIGINS_ENV:
    ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",")]
else:
    # Valores por defecto para desarrollo
    ALLOWED_ORIGINS = [
        "https://www.radarcol.com",
        "https://radarcol.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

# =====================================
# Configuración de Logging
# =====================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
