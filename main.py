from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime
import requests
import random
import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

# =====================================
# Configuración de Logging
# =====================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Análisis de Contratos Gubernamentales",
    description="""API para el análisis y consulta de contratos del sector público colombiano.

## Funcionalidades

- **Consulta de contratos**: Obtén información detallada de contratos gubernamentales
- **Filtrado avanzado**: Filtra por fecha, valor, entidad e ID específico
- **Análisis de riesgo**: Evaluación automática de niveles de riesgo y anomalías
- **Métricas agregadas**: Estadísticas totales y análisis de alto nivel

## Fuente de Datos

Los datos provienen de **SECOP II** (datos.gov.co), la plataforma oficial de contratación pública de Colombia.

## Campos Simulados

- `nivelRiesgo`: Algoritmo de evaluación de riesgo (simulado)
- `anomalia`: Detección de patrones anómalos (simulado)
- `contratosAltoRiesgo`: Porcentaje basado en análisis estadístico (simulado)
""",
    version="1.0.0",
    terms_of_service="https://www.datos.gov.co/",
    contact={
        "name": "Equipo de Análisis de Contratos",
        "email": "contacto@ejemplo.com",
    },
    license_info={
        "name": "Open Data License",
        "url": "https://www.datos.gov.co/",
    },
)

# =====================================
# Middleware de Logging
# =====================================
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log información de la petición entrante
        logger.info("="*80)
        logger.info(f"📥 Petición entrante:")
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
        logger.info(f"📤 Respuesta enviada:")
        logger.info(f"   • Status: {response.status_code}")
        logger.info(f"   • Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin', 'No configurado')}")
        logger.info("="*80 + "\n")
        
        return response

app.add_middleware(LoggingMiddleware)

# =====================================
# Configuración CORS
# =====================================

# Obtener orígenes desde variable de entorno o usar valores por defecto
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "")
if CORS_ORIGINS_ENV:
    ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",")]
    logger.info("\n" + "="*80)
    logger.info("🔧 CORS Origins cargados desde variable de entorno:")
    for origin in ALLOWED_ORIGINS:
        logger.info(f"   ✅ {origin}")
    logger.info("="*80 + "\n")
else:
    ALLOWED_ORIGINS = [
        "https://www.radarcol.com",  # Dominio de producción
        "https://radarcol.com",       # Dominio sin www
        "http://localhost:3000",      # Frontend desarrollo
        "http://127.0.0.1:3000",
        "http://localhost:3001",      # Backup port
    ]
    logger.info("\n" + "="*80)
    logger.info("⚠️  CORS Origins usando valores por defecto:")
    for origin in ALLOWED_ORIGINS:
        logger.info(f"   🔹 {origin}")
    logger.info("="*80 + "\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

logger.info("🚀 API de Análisis de Contratos Gubernamentales iniciada")
logger.info(f"🌐 Ambiente: {'PRODUCCION' if CORS_ORIGINS_ENV else 'DESARROLLO'}")
logger.info(f"📊 BASE_URL: {os.getenv('BASE_URL', 'https://www.datos.gov.co/resource/jbjy-vk9h.json')}")

BASE_URL = os.getenv("BASE_URL", "https://www.datos.gov.co/resource/jbjy-vk9h.json")

# =====================================
# Utilidades de Formateo
# =====================================

def estandarizar_texto(texto: str) -> str:
    """Estandariza el texto de contratos para formato de documento profesional.
    
    Aplica las siguientes reglas:
    - Capitaliza la primera letra del texto
    - Capitaliza después de puntos seguidos de espacio
    - Capitaliza después de puntos y coma cuando inicia nueva oración
    - Mantiene acrónimos y siglas
    - Limpia espacios extra y saltos de línea
    
    Args:
        texto (str): Texto a estandarizar
        
    Returns:
        str: Texto estandarizado
    """
    if not texto or not isinstance(texto, str):
        return ""
    
    # Limpiar el texto: eliminar saltos de línea extra y espacios múltiples
    texto = " ".join(texto.split())
    texto = texto.strip()
    
    if not texto:
        return ""
    
    # Convertir a minúsculas para empezar el proceso
    texto = texto.lower()
    
    # Capitalizar primera letra
    texto = texto[0].upper() + texto[1:] if len(texto) > 1 else texto.upper()
    
    # Capitalizar después de puntos seguidos de espacio
    import re
    
    # Patrón para punto seguido de espacio(s) y letra
    patron_punto = r'\. +([a-z])'
    texto = re.sub(patron_punto, lambda m: '. ' + m.group(1).upper(), texto)
    
    # Patrón para punto y coma seguido de espacio(s) y letra (cuando inicia nueva oración)
    patron_punto_coma = r'; +([a-z])'
    texto = re.sub(patron_punto_coma, lambda m: '; ' + m.group(1).upper(), texto)
    
    # Capitalizar después de dos puntos cuando inicia nueva oración
    patron_dos_puntos = r': +([a-z])'
    texto = re.sub(patron_dos_puntos, lambda m: ': ' + m.group(1).upper(), texto)
    
    return texto

# =====================================
# DTOs (Data Transfer Objects) Tipados
# =====================================

class NivelRiesgo(str, Enum):
    """Enumeración para los niveles de riesgo de los contratos."""
    ALTO = "Alto"
    MEDIO = "Medio"
    BAJO = "Bajo"
    SIN_ANALISIS = "Sin Analisis"


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
    Monto: str  # Se mantiene como string porque viene así desde la API
    FechaInicio: Optional[str]  # Puede ser null
    NivelRiesgo: NivelRiesgo
    Anomalia: float


class ContratosResponseModel(BaseModel):
    """Modelo de respuesta completa para el endpoint de contratos.
    
    Este modelo estructura toda la información de análisis de contratos,
    incluyendo métricas agregadas y detalles individuales.
    """
    metadata: MetadataModel
    totalContratosAnalizados: int
    contratosAltoRiesgo: int
    montoTotalCOP: float
    contratos: List[ContratoDetalleModel]


# =====================================
# DTOs para Análisis Detallado
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


# =====================================
# Endpoints
# =====================================

@app.get(
    "/",
    tags=["Información General"],
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


@app.get(
    "/contratos", 
    response_model=ContratosResponseModel,
    tags=["Análisis de Contratos"],
    summary="Consultar y analizar contratos gubernamentales",
    description="""Obtiene una lista de contratos gubernamentales con capacidades de filtrado avanzado y análisis de riesgo.

Este endpoint permite:
- Filtrar contratos por rango de fechas, valores monetarios, entidad contratante e ID específico
- Obtener métricas agregadas (total de contratos, monto total, contratos de alto riesgo)
- Análisis automático de niveles de riesgo y detección de anomalías
- Formateo profesional de descripciones de contratos

## Ejemplos de Uso

- Contratos del Ministerio de Salud: `?nombre_contrato=MINISTERIO SALUD`
- Contratos de alto valor en 2024: `?fecha_desde=2024-01-01&valor_minimo=50000000`
- Contrato específico: `?id_contrato=CO1.PCCNTR.1370606`
""",
    response_description="Lista de contratos con análisis de riesgo y métricas agregadas"
)
def obtener_contratos(
    limit: int = Query(
        default=100, 
        ge=1, 
        le=100, 
        description="Número máximo de contratos a retornar por consulta",
        example=10
    ),
    fecha_desde: Optional[str] = Query(
        default=None,
        description="Fecha de inicio mínima del contrato (formato: YYYY-MM-DD)",
        example="2023-01-01",
        regex="^\\d{4}-\\d{2}-\\d{2}$"
    ),
    fecha_hasta: Optional[str] = Query(
        default=None,
        description="Fecha de inicio máxima del contrato (formato: YYYY-MM-DD)",
        example="2024-12-31",
        regex="^\\d{4}-\\d{2}-\\d{2}$"
    ),
    valor_minimo: Optional[float] = Query(
        default=None,
        ge=0,
        description="Valor mínimo del contrato en pesos colombianos (COP)",
        example=1000000
    ),
    valor_maximo: Optional[float] = Query(
        default=None,
        ge=0,
        description="Valor máximo del contrato en pesos colombianos (COP)",
        example=100000000
    ),
    nombre_contrato: Optional[str] = Query(
        default=None,
        min_length=3,
        description="Buscar por nombre de la entidad contratante (búsqueda parcial, mínimo 3 caracteres)",
        example="MINISTERIO DE SALUD"
    ),
    id_contrato: Optional[str] = Query(
        default=None,
        description="Filtrar por ID específico del contrato (búsqueda exacta)",
        example="CO1.PCCNTR.1370606"
    )
) -> ContratosResponseModel:
    """Consulta y analiza contratos gubernamentales con filtros avanzados.
    
    Esta función implementa un sistema completo de consulta de contratos gubernamentales
    con capacidades de filtrado dinámico, análisis de riesgo y métricas agregadas.
    
    Args:
        limit: Número máximo de contratos a retornar (1-100)
        fecha_desde: Fecha mínima de inicio del contrato en formato YYYY-MM-DD
        fecha_hasta: Fecha máxima de inicio del contrato en formato YYYY-MM-DD
        valor_minimo: Valor mínimo del contrato en COP
        valor_maximo: Valor máximo del contrato en COP
        nombre_contrato: Texto para buscar en el nombre de la entidad contratante
        id_contrato: ID específico del contrato para búsqueda exacta
    
    Returns:
        ContratosResponseModel: Respuesta completa con:
            - metadata: Información sobre fuente de datos y campos simulados
            - totalContratosAnalizados: Número total de contratos que cumplen los filtros
            - contratosAltoRiesgo: Cantidad estimada de contratos de alto riesgo
            - montoTotalCOP: Suma total de los valores de los contratos filtrados
            - contratos: Lista de contratos con análisis de riesgo individual
    
    Raises:
        HTTPException: Si hay errores en la consulta a la API externa
    
    Example:
        >>> # Obtener contratos del Ministerio de Salud en 2024 por más de 10 millones
        >>> response = obtener_contratos(
        ...     nombre_contrato="MINISTERIO SALUD",
        ...     fecha_desde="2024-01-01",
        ...     valor_minimo=10000000,
        ...     limit=20
        ... )
    """
    # ====================================================================
    # 🔍 CONSTRUCCIÓN DINÁMICA DE FILTROS DE CONSULTA
    # ====================================================================
    where_conditions = []
    
    # ✅ FILTROS DE VALIDACIÓN BÁSICA: Asegurar que los datos esenciales existan
    where_conditions.append("fecha_de_inicio_del_contrato is not null")
    where_conditions.append("valor_del_contrato is not null")
    where_conditions.append("nombre_entidad is not null")
    
    # 📅 Filtros temporales: rango de fechas de inicio del contrato
    if fecha_desde:
        where_conditions.append(f"fecha_de_inicio_del_contrato >= '{fecha_desde}T00:00:00.000'")
    
    if fecha_hasta:
        where_conditions.append(f"fecha_de_inicio_del_contrato <= '{fecha_hasta}T23:59:59.999'")
    
    # 💰 Filtros monetarios: rango de valores del contrato
    if valor_minimo is not None:
        where_conditions.append(f"valor_del_contrato >= {valor_minimo}")
    
    if valor_maximo is not None:
        where_conditions.append(f"valor_del_contrato <= {valor_maximo}")
    
    # 🏢 Filtro por entidad: búsqueda insensible a mayúsculas en nombre de entidad
    if nombre_contrato:
        # Sanitización para prevenir inyección SQL y búsqueda case-insensitive
        nombre_limpio = nombre_contrato.upper().replace("'", "''")
        where_conditions.append(f"upper(nombre_entidad) like '%{nombre_limpio}%'")
    
    # 🆔 Filtro por ID: búsqueda exacta por identificador único del contrato
    if id_contrato:
        id_limpio = id_contrato.replace("'", "''")
        where_conditions.append(f"id_contrato = '{id_limpio}'")
    
    # Construcción de la cláusula WHERE final para SoQL
    where_clause = " AND ".join(where_conditions) if where_conditions else None
    
    # ====================================================================
    # 📊 CONSULTAS AGREGADAS CON FILTROS APLICADOS
    # ====================================================================
    # ----------------------------
    # 1️⃣ Agregados con SoQL (con filtros)
    # ----------------------------
    
    # 📈 Total de contratos que cumplen los criterios de filtrado
    count_params = {"$select": "count(*) as total"}
    if where_clause:
        count_params["$where"] = where_clause
        
    total_response = requests.get(BASE_URL, params=count_params)
    total_contratos = int(total_response.json()[0]["total"])

    # 💵 Suma total de valores monetarios de contratos filtrados
    sum_params = {"$select": "sum(valor_del_contrato) as monto_total"}
    if where_clause:
        sum_params["$where"] = where_clause
        
    sum_response = requests.get(BASE_URL, params=sum_params)
    monto_total = float(sum_response.json()[0]["monto_total"] or 0)

    # ⚠️ Análisis de riesgo: estimación de contratos de alto riesgo (20% heurístico)
    contratos_alto_riesgo = int(total_contratos * 0.2)

    # ====================================================================
    # 📄 OBTENCIÓN DE DATOS DETALLADOS DE CONTRATOS (ORDENADOS POR FECHA)
    # ====================================================================
    data_params = {
        "$limit": limit,
        "$order": "fecha_de_inicio_del_contrato DESC"  # Más recientes primero
    }
    if where_clause:
        data_params["$where"] = where_clause
    data_response = requests.get(BASE_URL, params=data_params)

    # ⚠️ Validación de respuesta exitosa de la API externa
    if data_response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "No se pudo obtener la información de contratos",
                "status_code": data_response.status_code,
                "message": "Error en la comunicación con la API de datos.gov.co"
            }
        )

    data = data_response.json()

    # ====================================================================
    # 🔄 PROCESAMIENTO Y TRANSFORMACIÓN DE DATOS
    # ====================================================================
    contratos_mapeados = []

    for contrato in data:
        # 📝 Estandarización de texto para presentación profesional
        descripcion_original = contrato.get("objeto_del_contrato", "")
        descripcion_estandarizada = estandarizar_texto(descripcion_original)
        
        # 🎲 Generación de análisis de riesgo simulado
        contratos_mapeados.append(ContratoDetalleModel(
            Contrato=ContratoInfoModel(
                Codigo=contrato.get("id_contrato", ""),
                Descripcion=descripcion_estandarizada
            ),
            Entidad=contrato.get("nombre_entidad", ""),
            Monto=contrato.get("valor_del_contrato", "0"),
            FechaInicio=contrato.get("fecha_de_inicio_del_contrato"),
            NivelRiesgo=random.choice(list(NivelRiesgo)),
            Anomalia=round(random.uniform(0, 100), 2)
        ))

    # ====================================================================
    # 🚀 CONSTRUCCIÓN DE RESPUESTA ESTRUCTURADA FINAL
    # ====================================================================
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


@app.get(
    "/contratos/{id}/analisis",
    response_model=ContratoAnalisisResponseModel,
    tags=["Análisis de Contratos"],
    summary="Obtener análisis detallado de un contrato específico",
    description="""Obtiene el análisis detallado con IA de un contrato específico.

Este endpoint proporciona:
- **Datos del contrato**: Información básica y nivel de riesgo
- **Resumen ejecutivo**: Análisis narrativo del contrato
- **Factores principales**: Variables que más influyen en el análisis
- **Valores SHAP**: Explicabilidad del modelo ML (feature importance)
- **Recomendaciones**: Acciones sugeridas basadas en el análisis
- **Métricas de confianza**: Probabilidad base y confianza del modelo

### Valores SHAP
Los valores SHAP (SHapley Additive exPlanations) explican el impacto de cada variable:
- **Valores positivos**: Aumentan la probabilidad de anomalía
- **Valores negativos**: Disminuyen la probabilidad de anomalía
- Ordenados por impacto absoluto (mayor a menor)

### Nota
🔬 Este endpoint retorna datos **mockeados** para propósitos de desarrollo y testing.
En producción, se conectará con el modelo de ML real.
""",
    response_description="Análisis detallado del contrato con explicabilidad del modelo"
)
def obtener_analisis_contrato(id: str):
    """Obtiene el análisis detallado de un contrato específico.
    
    Args:
        id (str): ID único del contrato a analizar
        
    Returns:
        ContratoAnalisisResponseModel: Datos del contrato y análisis completo con explicabilidad
        
    Note:
        Los datos retornados son simulados. En producción, se obtendrán del modelo ML real.
    """
    
    # ====================================================================
    # 🎭 DATOS MOCKEADOS - Para desarrollo y testing
    # ====================================================================
    
    # Datos del contrato mockeados
    contract_data = ContractDetailModel(
        id=id,
        codigo="CO-2025-123456",
        descripcion="Construcción y mejoramiento de vías terciarias en el departamento de Cundinamarca, incluyendo obras de drenaje, señalización y estabilización de taludes",
        entidad="Ministerio de Transporte",
        monto="2500000000",
        fechaInicio="2025-01-15",
        nivelRiesgo=NivelRiesgo.ALTO,
        anomalia=85.5
    )
    
    # Análisis mockeado con datos realistas
    analysis_data = AnalysisModel(
        contractId=id,
        resumenEjecutivo="""Este contrato presenta un nivel de riesgo alto (85.5% de probabilidad de anomalía) debido a varios factores críticos identificados por el modelo de análisis. El monto del contrato ($2.500 millones COP) es significativamente superior al promedio histórico para proyectos similares en la región, lo cual representa una señal de alerta importante.

El análisis revela que la combinación de contratación directa como modalidad de selección, junto con una duración proyectada de 365 días, aumenta considerablemente la exposición al riesgo. Históricamente, contratos con estas características han mostrado una mayor incidencia de sobrecostos y retrasos en la ejecución.

Se recomienda implementar mecanismos de supervisión reforzada y establecer hitos de control trimestral para mitigar los riesgos identificados. La entidad contratante debe considerar la viabilidad de un proceso de selección más competitivo que permita mayor transparencia y mejores condiciones contractuales.""",
        
        factoresPrincipales=[
            "Monto del contrato significativamente superior al promedio de mercado para obras similares (desviación de +45%)",
            "Modalidad de contratación directa sin proceso competitivo previo",
            "Duración del contrato (365 días) excede el promedio histórico para proyectos de infraestructura vial de esta magnitud",
            "Histórico de la entidad contratante muestra 3 contratos similares con adiciones presupuestales superiores al 20%",
            "Ubicación geográfica del proyecto en zona de difícil acceso, aumentando complejidad logística"
        ],
        
        recomendaciones=[
            "Establecer un comité de supervisión técnica con revisiones mensuales obligatorias del avance físico y financiero",
            "Implementar sistema de alertas tempranas para detectar desviaciones en cronograma o presupuesto superiores al 10%",
            "Solicitar garantías adicionales de cumplimiento por el 30% del valor del contrato debido al alto nivel de riesgo identificado",
            "Realizar auditorías técnicas trimestrales por parte de un tercero independiente especializado en infraestructura vial",
            "Establecer cláusulas de penalización por incumplimiento con valores disuasivos (mínimo 1% del valor por semana de retraso)"
        ],
        
        shapValues=[
            ShapValueModel(
                variable="monto_contrato",
                value=15.2,
                description="Monto del contrato",
                actualValue="2500000000"
            ),
            ShapValueModel(
                variable="tipo_contratacion",
                value=12.3,
                description="Tipo de contratación",
                actualValue="Contratación directa"
            ),
            ShapValueModel(
                variable="duracion_dias",
                value=10.8,
                description="Duración en días",
                actualValue="365"
            ),
            ShapValueModel(
                variable="historico_entidad",
                value=8.5,
                description="Histórico de la entidad",
                actualValue="3 contratos con adiciones >20%"
            ),
            ShapValueModel(
                variable="ubicacion_geografica",
                value=7.2,
                description="Complejidad de ubicación",
                actualValue="Zona rural de difícil acceso"
            ),
            ShapValueModel(
                variable="tipo_obra",
                value=5.8,
                description="Tipo de obra",
                actualValue="Infraestructura vial"
            ),
            ShapValueModel(
                variable="experiencia_contratista",
                value=-4.3,
                description="Experiencia del contratista",
                actualValue="8 años en obras similares"
            ),
            ShapValueModel(
                variable="indices_financieros",
                value=-3.1,
                description="Indicadores financieros",
                actualValue="Saludables"
            ),
            ShapValueModel(
                variable="certificaciones",
                value=-2.5,
                description="Certificaciones de calidad",
                actualValue="ISO 9001, ISO 14001"
            )
        ],
        
        probabilidadBase=45.0,
        confianza=87.5,
        fechaAnalisis="2025-12-23T10:30:00Z"
    )
    
    # ====================================================================
    # 🚀 CONSTRUCCIÓN DE RESPUESTA
    # ====================================================================
    return ContratoAnalisisResponseModel(
        contract=contract_data,
        analysis=analysis_data
    )
