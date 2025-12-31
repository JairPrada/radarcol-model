"""
Controllers para endpoints de salud del sistema.
"""
from fastapi import APIRouter
from datetime import datetime
import os

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
    return {"mensaje": "API de Análisis de Contratos Gubernamentales funcionando correctamente"}


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


@router.get(
    "/diagnostics",
    summary="Diagnóstico del sistema",
    description="Verifica el estado de componentes críticos incluyendo artefactos ML",
    response_description="Estado detallado de todos los componentes"
)
def diagnostics():
    """Diagnóstico completo del sistema.
    
    Returns:
        dict: Estado detallado de artefactos, servicios y configuración
    """
    from app.config import RUTA_ARTEFACTOS, GROQ_API_KEY
    from app.services.cache_service import CacheService
    
    # Verificar artefactos ML
    artifacts_status = {}
    required_files = [
        "modelo_isoforest.pkl",
        "centroide_semantico.npy", 
        "stats_entidades.json",
        "shap_explainer.pkl"
    ]
    
    for file in required_files:
        file_path = os.path.join(RUTA_ARTEFACTOS, file)
        artifacts_status[file] = {
            "exists": os.path.exists(file_path),
            "path": file_path,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
    
    # Verificar servicios
    try:
        cache = CacheService()
        cache_status = cache.is_enabled
    except Exception as e:
        cache_status = f"Error: {str(e)}"
    
    # Estado del motor de análisis
    try:
        from app.services.contract_service import ContractService
        motor = ContractService._obtener_motor()
        motor_status = {
            "initialized": motor is not None,
            "llm_available": motor.usar_llm if motor else False,
            "shap_available": motor.usar_shap if motor else False,
            "degraded_mode": getattr(motor, 'modo_solo_llm', False) if motor else True
        }
    except Exception as e:
        motor_status = {"error": str(e)}
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "artifacts_path": RUTA_ARTEFACTOS,
        "artifacts_status": artifacts_status,
        "services": {
            "cache": cache_status,
            "ml_engine": motor_status
        },
        "config": {
            "groq_configured": bool(GROQ_API_KEY),
            "working_directory": os.getcwd()
        }
    }
