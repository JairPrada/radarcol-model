"""
Modelos Pydantic para validación y serialización de datos.
"""
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


# =====================================
# Enums
# =====================================

class NivelRiesgo(str, Enum):
    """Enumeración para los niveles de riesgo de los contratos."""
    ALTO = "Alto"
    MEDIO = "Medio"
    BAJO = "Bajo"
    SIN_ANALISIS = "Sin Analisis"


# =====================================
# Modelos para Listado de Contratos
# =====================================

class MetadataModel(BaseModel):
    """Modelo para los metadatos de la respuesta."""
    fuenteDatos: str
    camposSimulados: List[str]


class ContratoInfoModel(BaseModel):
    """Modelo para la información básica del contrato."""
    Codigo: str
    Descripcion: str


class ContratoDetalleModel(BaseModel):
    """Modelo completo para el detalle de un contrato."""
    Contrato: ContratoInfoModel
    Entidad: str
    Monto: str
    FechaInicio: Optional[str]
    NivelRiesgo: NivelRiesgo
    Anomalia: float


class ContratosResponseModel(BaseModel):
    """Modelo de respuesta completa para el endpoint de contratos."""
    metadata: MetadataModel
    totalContratosAnalizados: int
    contratosAltoRiesgo: int
    montoTotalCOP: float
    contratos: List[ContratoDetalleModel]


# =====================================
# Modelos para Análisis Detallado
# =====================================

class ContractDetailModel(BaseModel):
    """Modelo para los datos básicos del contrato en el análisis detallado."""
    id: str
    codigo: str
    descripcion: str
    entidad: str
    monto: str
    fechaInicio: Optional[str]
    nivelRiesgo: NivelRiesgo
    anomalia: float


class ShapValueModel(BaseModel):
    """Modelo para un valor SHAP individual."""
    variable: str
    value: float
    description: str
    actualValue: str


class AnalysisModel(BaseModel):
    """Modelo para el análisis de IA del contrato."""
    contractId: str
    resumenEjecutivo: str
    factoresPrincipales: List[str]
    recomendaciones: List[str]
    shapValues: List[ShapValueModel]
    probabilidadBase: float
    confianza: float
    fechaAnalisis: str


class ContratoAnalisisResponseModel(BaseModel):
    """Modelo de respuesta completa para el análisis detallado de un contrato."""
    contract: ContractDetailModel
    analysis: AnalysisModel
