"""
Controllers para endpoints de salud del sistema.
"""
from fastapi import APIRouter
from datetime import datetime

from app.constants import HEALTH_CHECK_DESCRIPTION

router = APIRouter(tags=["Información General"])


@router.get(
    "/",
    summary="Estado de la API",
    description="Endpoint de verificación del estado y funcionamiento de la API",
    response_description="Mensaje de confirmación del funcionamiento de la API"
)
def root():
    """Endpoint de verificación del estado de la API.
    
    Returns:
        dict: Mensaje confirmando que la API está funcionando correctamente
    """
    return {"mensaje": "API de Análisis de Contratos Gubernamentales funcionando correctamente 🚀"}


@router.get(
    "/health",
    summary="Health check optimizado",
    description=HEALTH_CHECK_DESCRIPTION,
    response_description="Estado del servicio y timestamp"
)
def health_check():
    """Health check optimizado para mantener el servicio activo.
    
    Returns:
        dict: Estado, timestamp y uptime del servicio
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "radarcol-api",
        "version": "1.0.0"
    }
