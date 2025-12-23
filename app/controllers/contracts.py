"""
Controllers para endpoints de contratos gubernamentales.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.models import ContratosResponseModel, ContratoAnalisisResponseModel, MetadataModel
from app.services import ContractService
from app.constants import CONTRATOS_DESCRIPTION, ANALISIS_DESCRIPTION

router = APIRouter(tags=["Análisis de Contratos"])


@router.get(
    "/contratos",
    response_model=ContratosResponseModel,
    summary="Consultar y analizar contratos gubernamentales",
    description=CONTRATOS_DESCRIPTION,
    response_description="Lista de contratos con métricas agregadas y análisis de riesgo"
)
def obtener_contratos(
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Número máximo de contratos a retornar (entre 1 y 100)"
    ),
    fecha_desde: Optional[str] = Query(
        None,
        regex=r"^\d{4}-\d{2}-\d{2}$",
        description="Fecha de inicio mínima (formato: YYYY-MM-DD). Ejemplo: 2024-01-01",
        example="2024-01-01"
    ),
    fecha_hasta: Optional[str] = Query(
        None,
        regex=r"^\d{4}-\d{2}-\d{2}$",
        description="Fecha de inicio máxima (formato: YYYY-MM-DD). Ejemplo: 2024-12-31",
        example="2024-12-31"
    ),
    valor_minimo: Optional[float] = Query(
        None,
        ge=0,
        description="Valor mínimo del contrato en COP. Ejemplo: 1000000",
        example=1000000
    ),
    valor_maximo: Optional[float] = Query(
        None,
        ge=0,
        description="Valor máximo del contrato en COP. Ejemplo: 100000000",
        example=100000000
    ),
    nombre_contrato: Optional[str] = Query(
        None,
        min_length=3,
        description="Búsqueda por nombre de la entidad contratante (mínimo 3 caracteres). Ejemplo: 'ministerio'",
        example="ministerio"
    ),
    id_contrato: Optional[str] = Query(
        None,
        description="Búsqueda por ID específico del contrato. Ejemplo: 'ABC-2024-001'",
        example="ABC-2024-001"
    )
):
    """Obtiene lista de contratos con filtros opcionales.
    
    Args:
        limit: Número máximo de contratos a retornar
        fecha_desde: Fecha de inicio mínima
        fecha_hasta: Fecha de inicio máxima
        valor_minimo: Valor mínimo del contrato
        valor_maximo: Valor máximo del contrato
        nombre_contrato: Nombre de la entidad contratante
        id_contrato: ID específico del contrato
        
    Returns:
        ContratosResponseModel: Respuesta con métricas y lista de contratos
    """
    # Construir cláusula WHERE dinámica
    filtros = [
        "fecha_de_inicio_del_contrato is not null",
        "valor_del_contrato is not null",
        "nombre_entidad is not null"
    ]
    
    if fecha_desde:
        filtros.append(f"fecha_de_inicio_del_contrato >= '{fecha_desde}'")
    if fecha_hasta:
        filtros.append(f"fecha_de_inicio_del_contrato <= '{fecha_hasta}'")
    if valor_minimo is not None:
        filtros.append(f"valor_del_contrato >= {valor_minimo}")
    if valor_maximo is not None:
        filtros.append(f"valor_del_contrato <= {valor_maximo}")
    if nombre_contrato:
        filtros.append(f"nombre_entidad like '%{nombre_contrato}%'")
    if id_contrato:
        filtros.append(f"id_contrato = '{id_contrato}'")
    
    where_clause = " AND ".join(filtros)
    
    # Obtener datos del servicio
    total_contratos, monto_total, contratos_alto_riesgo, contratos_mapeados = \
        ContractService.obtener_contratos_filtrados(limit, where_clause)
    
    # Construir respuesta
    return ContratosResponseModel(
        metadata=MetadataModel(
            fuenteDatos="datos.gov.co (SECOP II - Sistema Electrónico de Contratación Pública)",
            camposSimulados=[
                "nivelRiesgo",
                "anomalia",
                "contratosAltoRiesgo"
            ]
        ),
        totalContratosAnalizados=total_contratos,
        contratosAltoRiesgo=contratos_alto_riesgo,
        montoTotalCOP=round(monto_total, 2),
        contratos=contratos_mapeados
    )


@router.get(
    "/contratos/{id}/analisis",
    response_model=ContratoAnalisisResponseModel,
    summary="Obtener análisis detallado de un contrato específico",
    description=ANALISIS_DESCRIPTION,
    response_description="Análisis detallado del contrato con explicabilidad del modelo"
)
def obtener_analisis_contrato(id: str):
    """Obtiene el análisis detallado de un contrato específico.
    
    Args:
        id: ID único del contrato a analizar
        
    Returns:
        ContratoAnalisisResponseModel: Datos del contrato y análisis completo
    """
    # Obtener datos del contrato
    contrato = ContractService.obtener_contrato_por_id(id)
    
    # Generar análisis
    contract_data, analysis_data = ContractService.generar_analisis_contrato(id, contrato)
    
    # Construir respuesta
    return ContratoAnalisisResponseModel(
        contract=contract_data,
        analysis=analysis_data
    )
