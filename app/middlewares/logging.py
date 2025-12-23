"""
Middleware de logging para trazabilidad de peticiones.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para registrar detalles de cada petición HTTP."""
    
    async def dispatch(self, request: Request, call_next):
        """Procesa y registra información de la petición y respuesta.
        
        Args:
            request: Objeto Request de FastAPI
            call_next: Función para continuar el procesamiento
            
        Returns:
            Response: Respuesta procesada
        """
        # Log información de la petición entrante
        logger.info("=" * 80)
        logger.info("📥 Petición entrante:")
        logger.info(f"   • Método: {request.method}")
        logger.info(f"   • Path: {request.url.path}")
        logger.info(f"   • Origin: {request.headers.get('origin', 'No especificado')}")
        logger.info(f"   • Host: {request.headers.get('host', 'No especificado')}")
        logger.info(f"   • User-Agent: {request.headers.get('user-agent', 'No especificado')}")
        
        # Log headers CORS específicos (si existen)
        if request.method == "OPTIONS":
            logger.info("   🔹 Petición CORS preflight detectada")
            logger.info(f"   • Access-Control-Request-Method: {request.headers.get('access-control-request-method', 'N/A')}")
            logger.info(f"   • Access-Control-Request-Headers: {request.headers.get('access-control-request-headers', 'N/A')}")
        
        # Procesar la petición
        response = await call_next(request)
        
        # Log respuesta
        logger.info("📤 Respuesta enviada:")
        logger.info(f"   • Status: {response.status_code}")
        logger.info(f"   • Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin', 'No configurado')}")
        logger.info("=" * 80 + "\n")
        
        return response
