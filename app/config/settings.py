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

# Ruta de artefactos ML - Buscar en múltiples ubicaciones posibles
RUTA_ARTEFACTOS = os.getenv("RUTA_ARTEFACTOS")
if not RUTA_ARTEFACTOS:
    # Buscar ubicaciones comunes para los artefactos
    possible_paths = [
        "data/artifacts",
        "./data/artifacts", 
        "artifacts",
        "./artifacts",
        "/opt/render/project/data/artifacts",  # Ruta común en Render
        "/app/data/artifacts"  # Ruta común en Docker
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "modelo_isoforest.pkl")):
            RUTA_ARTEFACTOS = path
            break
    
    # Valor por defecto si no se encuentra
    if not RUTA_ARTEFACTOS:
        RUTA_ARTEFACTOS = "data/artifacts"
        
print(f"🔍 Configuración de artefactos: {RUTA_ARTEFACTOS}")

# =====================================
# Configuración de Embeddings (NLP)
# =====================================
# IMPORTANTE: Los modelos de embeddings consumen mucha memoria (400-800MB)
# Deshabilitar en ambientes con < 1GB RAM disponible (ej: free tier de hosting)

# Habilitar/Deshabilitar análisis semántico con embeddings
# False = Solo análisis ML + LLM (Bajo uso de memoria ~200MB)
# True = Análisis completo con embeddings (Alto uso de memoria ~600-800MB)
ENABLE_EMBEDDINGS = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"

# Modelo de embeddings a usar (solo si ENABLE_EMBEDDINGS=true)
# Opciones recomendadas por tamaño:
#   - 'paraphrase-multilingual-MiniLM-L12-v2' (~120MB) - RECOMENDADO para RAM limitada
#   - 'distiluse-base-multilingual-cased-v2' (~135MB)
#   - 'hiiamsid/sentence_similarity_spanish_es' (~500MB) - Mejor calidad, más memoria
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", 
    "paraphrase-multilingual-MiniLM-L12-v2"  # Modelo ligero por defecto
)

print(f"🧠 Embeddings habilitados: {ENABLE_EMBEDDINGS}")
if ENABLE_EMBEDDINGS:
    print(f"   Modelo: {EMBEDDING_MODEL}")

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
