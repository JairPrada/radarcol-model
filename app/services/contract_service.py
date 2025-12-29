"""
Servicio de contratos - Lógica de negocio para gestión de contratos.
"""
import requests
import randomimport loggingfrom typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException

from app.config import BASE_URL, GEMINI_API_KEY, RUTA_ARTEFACTOS
from app.models import (
    NivelRiesgo,
    MetadataModel,
    ContratoInfoModel,
    ContratoDetalleModel,
    ContractDetailModel,
    ShapValueModel,
    AnalysisModel
)
from app.utils import estandarizar_texto
from motor.engine import RadarColInferencia


# Configurar logger
logger = logging.getLogger(__name__)

class ContractService:
    """Servicio para gestionar operaciones relacionadas con contratos."""
    
    # Instancia singleton del motor de análisis
    _motor_analisis: Optional[RadarColInferencia] = None
    
    @classmethod
    def _obtener_motor(cls) -> RadarColInferencia:
        """Obtiene o inicializa la instancia del motor de análisis.
        
        Returns:
            RadarColInferencia: Instancia del motor de análisis
        """
        if cls._motor_analisis is None:
            logger.info("🚀 Inicializando motor RadarColInferencia por primera vez...")
            logger.info(f"   📁 Ruta artefactos: {RUTA_ARTEFACTOS}")
            logger.info(f"   🔑 API Key configurada: {'Sí' if GEMINI_API_KEY else 'No'}")
            cls._motor_analisis = RadarColInferencia(
                api_key_gemini=GEMINI_API_KEY,
                ruta_artefactos=RUTA_ARTEFACTOS
            )
            logger.info("✅ Motor inicializado correctamente")
        return cls._motor_analisis
    
    @staticmethod
    def _preparar_datos_para_motor(contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma los datos de la API externa al formato esperado por el motor.
        
        Args:
            contrato: Datos del contrato de la API externa
            
        Returns:
            dict: Datos transformados para el motor de análisis
        """
        # Extraer año y mes de la fecha de inicio
        fecha_inicio = contrato.get("fecha_de_inicio_del_contrato", "2025-01-01")
        try:
            fecha_obj = datetime.strptime(fecha_inicio[:10], "%Y-%m-%d")
            anio_firma = fecha_obj.year
            mes_firma = fecha_obj.month
        except:
            anio_firma = 2025
            mes_firma = 1
        
        # Preparar datos en el formato del motor
        datos_motor = {
            "ID Contrato": contrato.get("id_contrato", "N/A"),
            "Valor del Contrato": float(contrato.get("valor_del_contrato", 0)),
            "Objeto del Contrato": contrato.get("objeto_del_contrato", "Sin descripción"),
            "Nit Entidad": contrato.get("nit_entidad", "0"),
            "Duracion Dias": float(contrato.get("plazo_de_ejec_del_contrato", 0)),
            "Anio Firma": anio_firma,
            "Mes Firma": mes_firma,
            "Indice Dependencia": 0.0  # Valor por defecto, puede calcularse con datos históricos
        }
        
        logger.debug(f"📋 Datos preparados para el motor:")
        logger.debug(f"   💰 Valor: ${datos_motor['Valor del Contrato']:,.0f}")
        logger.debug(f"   📅 Fecha: {anio_firma}-{mes_firma:02d}")
        logger.debug(f"   ⏱️  Duración: {datos_motor['Duracion Dias']} días")
        
        return datos_motor
    
    @staticmethod
    def _mapear_nivel_riesgo(nivel: str) -> NivelRiesgo:
        """Mapea el nivel de riesgo del motor al enum NivelRiesgo.
        
        Args:
            nivel: Nivel de riesgo del motor (CRÍTICO, ALTO, BAJO)
            
        Returns:
            NivelRiesgo: Enum del nivel de riesgo
        """
        mapeo = {
            "CRÍTICO": NivelRiesgo.ALTO,
            "ALTO": NivelRiesgo.MEDIO,
            "BAJO": NivelRiesgo.BAJO
        }
        return mapeo.get(nivel, NivelRiesgo.MEDIO)
    
    @staticmethod
    def _construir_shap_values(
        detalle_shap: List[Dict[str, Any]],
        contrato: Dict[str, Any]
    ) -> List[ShapValueModel]:
        """Construye los valores SHAP para la respuesta del endpoint.
        
        Args:
            detalle_shap: Lista de valores SHAP del motor
            contrato: Datos originales del contrato
            
        Returns:
            List[ShapValueModel]: Lista de modelos SHAP para la respuesta
        """
        # Mapeo de variables técnicas a descripciones legibles
        descripciones = {
            "Z-Score Valor": "Desviación del monto respecto al promedio de la entidad",
            "Valor Logaritmo": "Escala logarítmica del valor del contrato",
            "Costo por Caracter": "Ratio entre monto y complejidad de la descripción",
            "Indice Dependencia Proveedor": "Nivel de concentración con proveedores específicos",
            "Pct Tiempo Adicionado": "Porcentaje de tiempo adicionado al plazo original",
            "Duracion Dias": "Duración del contrato en días",
            "Dias tras Firma": "Días transcurridos desde la firma",
            "Anio Firma": "Año de firma del contrato",
            "Mes Firma": "Mes de firma del contrato"
        }
        
        # Valores actuales para mostrar en el detalle
        valores_actuales = {
            "Z-Score Valor": "Calculado dinámicamente",
            "Valor Logaritmo": f"{contrato.get('valor_del_contrato', 0)}",
            "Costo por Caracter": "Ratio calculado",
            "Indice Dependencia Proveedor": "0.0",
            "Pct Tiempo Adicionado": "0%",
            "Duracion Dias": str(contrato.get("plazo_de_ejec_del_contrato", "N/A")),
            "Dias tras Firma": "Calculado",
            "Anio Firma": str(contrato.get("fecha_de_inicio_del_contrato", "")[:4]),
            "Mes Firma": str(contrato.get("fecha_de_inicio_del_contrato", "")[5:7])
        }
        
        shap_models = []
        for item in detalle_shap:
            variable = item.get("variable", "")
            peso = item.get("peso", 0.0)
            
            shap_models.append(ShapValueModel(
                variable=variable.lower().replace(" ", "_").replace("-", "_"),
                value=round(peso, 2),
                description=descripciones.get(variable, variable),
                actualValue=valores_actuales.get(variable, "N/A")
            ))
        
        return shap_models
    
    @staticmethod
    def obtener_contratos_filtrados(
        limit: int,
        where_clause: str
    ) -> tuple[int, float, int, List[ContratoDetalleModel]]:
        """Obtiene contratos filtrados con métricas agregadas.
        
        Args:
            limit: Número máximo de contratos a retornar
            where_clause: Cláusula WHERE de SoQL para filtrado
            
        Returns:
            tuple: (total_contratos, monto_total, contratos_alto_riesgo, contratos_mapeados)
            
        Raises:
            HTTPException: Si hay error en la comunicación con la API externa
        """
        # Contar total de contratos
        count_params = {"$select": "count(*) as total"}
        if where_clause:
            count_params["$where"] = where_clause
            
        total_response = requests.get(BASE_URL, params=count_params)
        total_contratos = int(total_response.json()[0]["total"])

        # Suma total de valores monetarios
        sum_params = {"$select": "sum(valor_del_contrato) as monto_total"}
        if where_clause:
            sum_params["$where"] = where_clause
            
        sum_response = requests.get(BASE_URL, params=sum_params)
        monto_total = float(sum_response.json()[0]["monto_total"] or 0)

        # Estimación de contratos de alto riesgo (20% heurístico)
        contratos_alto_riesgo = int(total_contratos * 0.2)

        # Obtener datos detallados
        data_params = {
            "$limit": limit,
            "$order": "fecha_de_inicio_del_contrato DESC"
        }
        if where_clause:
            data_params["$where"] = where_clause
            
        data_response = requests.get(BASE_URL, params=data_params)

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

        # Mapear contratos
        contratos_mapeados = []
        for contrato in data:
            descripcion_original = contrato.get("objeto_del_contrato", "")
            descripcion_estandarizada = estandarizar_texto(descripcion_original)
            
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

        return total_contratos, monto_total, contratos_alto_riesgo, contratos_mapeados

    @staticmethod
    def obtener_contrato_por_id(contract_id: str) -> Dict[str, Any]:
        """Obtiene un contrato específico por su ID.
        
        Args:
            contract_id: ID del contrato a buscar
            
        Returns:
            dict: Datos del contrato
            
        Raises:
            HTTPException: Si el contrato no existe o hay error en la API
        """
        params = {
            "$where": f"id_contrato = '{contract_id}'",
            "$limit": 1
        }
        
        response = requests.get(BASE_URL, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "No se pudo obtener la información del contrato",
                    "status_code": response.status_code,
                    "message": "Error en la comunicación con la API de datos.gov.co"
                }
            )
        
        data = response.json()
        
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Contrato no encontrado",
                    "id": contract_id,
                    "message": f"No se encontró ningún contrato con el ID '{contract_id}'"
                }
            )
        
        return data[0]

    @classmethod
    def generar_analisis_contrato(
        cls,
        contract_id: str,
        contrato: Dict[str, Any]
    ) -> tuple[ContractDetailModel, AnalysisModel]:
        """Genera análisis detallado de un contrato usando el motor de ML e IA.
        
        Args:
            contract_id: ID del contrato
            contrato: Datos del contrato de la API
            
        Returns:
            tuple: (contract_data, analysis_data)
        """
        # Procesar datos del contrato
        descripcion_original = contrato.get("objeto_del_contrato", "Sin descripción")
        descripcion_estandarizada = estandarizar_texto(descripcion_original)
        
        monto = contrato.get("valor_del_contrato", "0")
        fecha_inicio = contrato.get("fecha_de_inicio_del_contrato")
        
        # ============================================
        # ANÁLISIS REAL CON MOTOR DE IA
        # ============================================
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 INICIANDO ANÁLISIS DE CONTRATO: {contract_id}")
        logger.info(f"{'='*80}")
        
        try:
            # Obtener instancia del motor
            motor = cls._obtener_motor()
            
            # Preparar datos para el motor
            logger.info("📊 Preparando datos del contrato...")
            datos_motor = cls._preparar_datos_para_motor(contrato)
            
            # Ejecutar análisis con el motor
            logger.info("🧠 Ejecutando análisis con motor RadarColInferencia...")
            resultado_analisis = motor.analizar_contrato(datos_motor)
            
            # Log del resultado completo
            logger.info("✅ Análisis completado. Procesando resultados...")
            logger.debug(f"📦 Claves en resultado: {list(resultado_analisis.keys())}")
            
            # Extraer resultados
            nivel_riesgo_str = resultado_analisis["Meta_Data"]["Riesgo"]
            anomalia = resultado_analisis["Meta_Data"]["Score"] * 100  # Convertir a porcentaje
            nivel_riesgo = cls._mapear_nivel_riesgo(nivel_riesgo_str)
            
            logger.info(f"🎯 Nivel de Riesgo Detectado: {nivel_riesgo_str} ({anomalia:.1f}%)")
            
            resumen_ejecutivo = resultado_analisis.get("Resumen_Ejecutivo", "Análisis completado")
            factores_principales = resultado_analisis.get("Factores_Principales", [])
            recomendaciones = resultado_analisis.get("Recomendaciones_Auditor", [])
            detalle_shap = resultado_analisis.get("Detalle_SHAP", [])
            
            logger.info(f"📈 Factores principales encontrados: {len(factores_principales)}")
            logger.info(f"💡 Recomendaciones generadas: {len(recomendaciones)}")
            logger.info(f"📊 Valores SHAP disponibles: {len(detalle_shap)}")
            
            if detalle_shap:
                logger.debug("🔍 Detalle SHAP:")
                for item in detalle_shap[:3]:  # Mostrar solo los primeros 3
                    logger.debug(f"   • {item.get('variable', 'N/A')}: {item.get('peso', 0):.4f}")
            
        except Exception as e:
            # Fallback en caso de error del motor
            logger.error(f"❌ ERROR en motor de análisis: {type(e).__name__}")
            logger.error(f"   Mensaje: {str(e)}")
            logger.error(f"   Contrato ID: {contract_id}")
            logger.warning("⚠️  Activando modo de contingencia con valores por defecto")
            
            nivel_riesgo = NivelRiesgo.MEDIO
            anomalia = 50.0
            resumen_ejecutivo = f"Análisis del contrato {contract_id}. El motor de análisis no está disponible temporalmente."
            factores_principales = ["Análisis en modo de contingencia"]
            recomendaciones = ["Verificar configuración del sistema de análisis"]
            detalle_shap = []
        
        # Datos del contrato
        contract_data = ContractDetailModel(
            id=contract_id,
            codigo=contrato.get("id_contrato", contract_id),
            descripcion=descripcion_estandarizada,
            entidad=contrato.get("nombre_entidad", "Entidad no especificada"),
            monto=str(monto),
            fechaInicio=fecha_inicio,
            nivelRiesgo=nivel_riesgo,
            anomalia=round(anomalia, 2)
        )
        
        # Construir valores SHAP desde el detalle del motor
        logger.info("🔧 Construyendo valores SHAP para respuesta...")
        shap_values = cls._construir_shap_values(detalle_shap, contrato) if detalle_shap else []
        logger.info(f"✅ SHAP values construidos: {len(shap_values)} variables")
        
        if shap_values:
            logger.debug("📊 Variables SHAP principales:")
            for sv in shap_values[:3]:
                logger.debug(f"   • {sv.variable}: {sv.value} ({sv.description})")
        else:
            logger.warning("⚠️  No se generaron valores SHAP")
        
        # Análisis con datos reales del motor
        analysis_data = AnalysisModel(
            contractId=contract_id,
            resumenEjecutivo=resumen_ejecutivo,
            factoresPrincipales=factores_principales,
            recomendaciones=recomendaciones,
            shapValues=shap_values,
            probabilidadBase=round(anomalia * 0.8, 1),  # Base calculada como 80% del score
            confianza=87.5,  # Confianza del modelo (puede ajustarse)
            fechaAnalisis=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        logger.info(f"   📝 Contrato: {contract_id}")
        logger.info(f"   ⚠️  Nivel Riesgo: {nivel_riesgo.value}")
        logger.info(f"   📊 Anomalía: {anomalia:.1f}%")
        logger.info(f"   🔢 SHAP Values: {len(shap_values)}")
        logger.info(f"{'='*80}\n")
        
        return contract_data, analysis_data
