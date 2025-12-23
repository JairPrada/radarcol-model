"""
Punto de entrada principal de la aplicación FastAPI.
API de Análisis de Contratos Gubernamentales.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, CORS_ORIGINS_ENV, BASE_URL
from app.constants import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    API_TERMS_OF_SERVICE,
    API_CONTACT,
    API_LICENSE_INFO
)
from app.middlewares import LoggingMiddleware
from app.controllers import health_router, contracts_router

# =====================================
# Configuración de Logging
# =====================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================
# Inicialización de la Aplicación
# =====================================
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    terms_of_service=API_TERMS_OF_SERVICE,
    contact=API_CONTACT,
    license_info=API_LICENSE_INFO,
)

# =====================================
# Configuración de Middlewares
# =====================================
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# =====================================
# Logging de Configuración al Inicio
# =====================================
if CORS_ORIGINS_ENV:
    logger.info("\n" + "="*80)
    logger.info("🔧 CORS Origins cargados desde variable de entorno:")
    for origin in ALLOWED_ORIGINS:
        logger.info(f"   ✅ {origin}")
    logger.info("="*80 + "\n")
else:
    logger.info("\n" + "="*80)
    logger.info("⚠️  CORS Origins usando valores por defecto:")
    for origin in ALLOWED_ORIGINS:
        logger.info(f"   🔹 {origin}")
    logger.info("="*80 + "\n")

logger.info("🚀 API de Análisis de Contratos Gubernamentales iniciada")
logger.info(f"🌐 Ambiente: {'PRODUCCION' if CORS_ORIGINS_ENV else 'DESARROLLO'}")
logger.info(f"📊 BASE_URL: {BASE_URL}")

# =====================================
# Registro de Routers
# =====================================
app.include_router(health_router)
app.include_router(contracts_router)
