"""Archivo de inicialización del módulo controllers."""
from .health_controller import router as health_router
from .contract_controller import router as contracts_router

__all__ = ["health_router", "contracts_router"]
