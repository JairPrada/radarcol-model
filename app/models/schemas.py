"""
Modelos Pydantic para validación y serialización de datos.
"""
from pydantic import BaseModel, Field, ConfigDict
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
    variable: str = Field(..., description="Nombre técnico de la variable")
    value: float = Field(..., description="Peso o impacto de la variable en el análisis")
    description: str = Field(..., description="Descripción legible de la variable")
    actualValue: str = Field(..., description="Valor actual de la variable en el contrato")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "variable": "z_score_valor",
                "value": 9.12,
                "description": "Desviación del monto respecto al promedio de la entidad",
                "actualValue": "9.12"
            }
        }
    )


class AnalysisModel(BaseModel):
    """Modelo para el análisis de IA del contrato."""
    contractId: str = Field(..., description="ID único del contrato analizado")
    resumenEjecutivo: str = Field(..., description="Resumen ejecutivo generado por IA")
    factoresPrincipales: List[str] = Field(..., description="Factores principales que influyen en el riesgo")
    recomendaciones: List[str] = Field(..., description="Recomendaciones del auditor para supervisión")
    shapValues: List[ShapValueModel] = Field(default_factory=list, description="Valores SHAP de explicabilidad del modelo")
    probabilidadBase: float = Field(..., description="Probabilidad base de anomalía")
    confianza: float = Field(..., description="Nivel de confianza del modelo (%)")
    fechaAnalisis: str = Field(..., description="Fecha y hora del análisis")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "contractId": "CO1.PCCNTR.6385899",
                "resumenEjecutivo": "Análisis detectó anomalía crítica...",
                "factoresPrincipales": ["Factor 1", "Factor 2"],
                "recomendaciones": ["Recomendación 1", "Recomendación 2"],
                "shapValues": [],
                "probabilidadBase": 70.4,
                "confianza": 87.5,
                "fechaAnalisis": "2025-12-29T16:47:37Z"
            }
        }
    )


class ContratoAnalisisResponseModel(BaseModel):
    """Modelo de respuesta completa para el análisis detallado de un contrato."""
    contract: ContractDetailModel
    analysis: AnalysisModel
