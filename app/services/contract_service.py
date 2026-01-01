"""
Servicio de contratos - Lógica de negocio para gestión de contratos.
"""
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException

from app.config import BASE_URL, GROQ_API_KEY, RUTA_ARTEFACTOS
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
from app.core import RadarColInferencia
from app.services.cache_service import cache_service


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
            logger.info("Inicializando motor RadarColInferencia con configuración Groq...")
            logger.info(f"   Ruta artefactos: {RUTA_ARTEFACTOS}")
            logger.info(f"   Groq API Key configurada: {'Sí' if GROQ_API_KEY else 'No (solo ML)'}")
            
            cls._motor_analisis = RadarColInferencia(
                groq_api_key=GROQ_API_KEY,  # Usa Groq API key
                ruta_artefactos=RUTA_ARTEFACTOS
            )
            
            logger.info("Motor inicializado correctamente")
            logger.info(f"   LLM disponible: {cls._motor_analisis.usar_llm}")
            logger.info(f"   Cliente Groq: {cls._motor_analisis.client is not None}")
            
        return cls._motor_analisis
    
    @classmethod
    def _preparar_datos_para_motor(cls, contrato: Dict[str, Any]) -> Dict[str, Any]:
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
        
        logger.debug(f"Datos preparados para el motor:")
        logger.debug(f"   💰 Valor: ${datos_motor['Valor del Contrato']:,.0f}")
        logger.debug(f"   📅 Fecha: {anio_firma}-{mes_firma:02d}")
        logger.debug(f"   ⏱️  Duración: {datos_motor['Duracion Dias']} días")
        
        return datos_motor
    
    @classmethod
    def _mapear_nivel_riesgo(cls, nivel: str) -> NivelRiesgo:
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
    
    @classmethod
    def _construir_shap_values(
        cls,
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
        logger.debug(f"🔧 Construyendo SHAP values desde {len(detalle_shap)} elementos")
        
        # Validar entrada
        if not detalle_shap or not isinstance(detalle_shap, list):
            logger.warning("detalle_shap está vacío o no es una lista")
            return []
            
        if not contrato or not isinstance(contrato, dict):
            logger.warning("contrato está vacío o no es un dict")
            return []
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
        for i, item in enumerate(detalle_shap):
            try:
                # Validar estructura del item
                if not isinstance(item, dict):
                    logger.warning(f"Item SHAP {i} no es un dict: {type(item)}")
                    continue
                    
                # Extraer datos del item
                variable = item.get("variable", "")
                valor = item.get("valor", 0.0)  # El motor usa "valor" no "value"
                
                # Validar campos requeridos
                if not variable:
                    logger.warning(f"Item SHAP {i} sin campo 'variable'")
                    continue
                    
                if not isinstance(valor, (int, float)):
                    logger.warning(f"Item SHAP {i} 'valor' no es numérico: {type(valor)}")
                    try:
                        valor = float(valor)
                    except (ValueError, TypeError):
                        valor = 0.0
                
                # Normalizar nombre de variable
                variable_normalizada = variable.lower().replace(" ", "_").replace("-", "_")
                
                # Crear modelo SHAP
                shap_model = ShapValueModel(
                    variable=variable_normalizada,
                    value=round(float(valor), 4),  # Más precisión
                    description=descripciones.get(variable, f"Variable: {variable}"),
                    actualValue=valores_actuales.get(variable, "Calculado")
                )
                
                shap_models.append(shap_model)
                logger.debug(f"   ✓ SHAP {i}: {variable} = {valor:.4f}")
                
            except Exception as e:
                logger.error(f"Error procesando item SHAP {i}: {e}")
                logger.error(f"   Item data: {item}")
                continue
        
        # Ordenar por importancia (valor absoluto) descendente
        shap_models.sort(key=lambda x: abs(x.value), reverse=True)
        
        logger.info(f"✅ Construidos {len(shap_models)} SHAP values válidos")
        if shap_models:
            logger.debug(f"   Top 3 variables más importantes:")
            for i, model in enumerate(shap_models[:3]):
                logger.debug(f"   {i+1}. {model.variable}: {model.value:.4f} ({model.description})")
        
        return shap_models
    
    @classmethod
    def obtener_contratos_filtrados(
        cls,
        where_clause: str,
        analyze_all: bool = True,
        return_limit: int = 10
    ) -> tuple[int, float, int, List[ContratoDetalleModel]]:
        """Obtiene contratos filtrados con análisis rápido de muestra.
        
        NUEVO: Consulta y analiza solo los primeros 10 contratos que cumplan los filtros
        para generar una respuesta rápida. Las estadísticas se calculan sobre esta muestra.
        
        Args:
            where_clause: Cláusula WHERE de SoQL para filtrado
            analyze_all: Ignorado, siempre analiza solo 10 contratos (modo muestra)
            return_limit: Número de contratos a consultar y analizar (default: 10)
            
        Returns:
            tuple: (total_contratos_muestra, monto_total_muestra, contratos_alto_riesgo, contratos_mapeados)
            
        Raises:
            HTTPException: Si hay error en la comunicación con la API externa
        """
        # Filtros de calidad de datos
        filtros_calidad = [
            "valor_del_contrato < 50000000000",  # Menos de 50 mil millones (outliers)
            "valor_del_contrato > 0",  # Valores positivos
            "fecha_de_inicio_del_contrato >= '2010-01-01'",  # Fechas válidas desde 2010
            "fecha_de_inicio_del_contrato <= '2026-12-31'",  # Fechas válidas hasta 2026
            "objeto_del_contrato IS NOT NULL",  # Descripción no nula
            "LENGTH(objeto_del_contrato) > 10"  # Descripción con contenido mínimo
        ]
        
        # Combinar filtros de calidad con filtros del usuario
        filtros_combinados = filtros_calidad.copy()
        if where_clause:
            filtros_combinados.append(f"({where_clause})")
        
        where_final = " AND ".join(filtros_combinados)
        
        print(f"🔍 Filtros aplicados: {len(filtros_combinados)} filtros de calidad + filtros usuario")

        # ==================== SISTEMA DE CACHÉ ====================
        # Generar hash único de filtros para caché (incluye limit=10)
        filtro_hash = cache_service.generate_filter_hash({
            "where_clause": where_clause,
            "analyze_all": False,  # Solo 10 contratos
            "return_limit": return_limit,
            "sample_mode": True  # Modo muestra rápida
        })
        
        # Intentar obtener estadísticas del caché
        stats_cached = cache_service.get_estadisticas_cached(filtro_hash)
        
        if stats_cached and cache_service.is_enabled:
            print(f"\n✅ USANDO CACHÉ - Stats encontradas")
            print(f"   Total contratos: {stats_cached['total_contratos']:,}")
            print(f"   Alto riesgo: {stats_cached['contratos_alto_riesgo']:,}")
            print(f"   Monto total: ${stats_cached['monto_total_cop']:,.2f} COP\n")
            
            # Obtener IDs de contratos (ordenados por fecha DESC)
            ids_params = {
                "$select": "id_contrato,nombre_entidad,valor_del_contrato,fecha_de_inicio_del_contrato,objeto_del_contrato",
                "$limit": return_limit,
                "$order": "fecha_de_inicio_del_contrato DESC"
            }
            if where_final:
                ids_params["$where"] = where_final
            
            ids_response = requests.get(BASE_URL, params=ids_params)
            contratos_data = ids_response.json()
            
            # Intentar obtener análisis del caché
            ids_contratos = [c.get("id_contrato") for c in contratos_data if c.get("id_contrato")]
            analisis_cached = cache_service.get_analisis_ligero_batch(ids_contratos)
            
            # Construir respuesta con datos cached
            contratos_mapeados = []
            for contrato in contratos_data:
                id_contrato = contrato.get("id_contrato")
                cached_data = analisis_cached.get(id_contrato)
                
                if cached_data:
                    # Usar datos del caché
                    descripcion = estandarizar_texto(contrato.get("objeto_del_contrato", ""))
                    contratos_mapeados.append(ContratoDetalleModel(
                        Contrato=ContratoInfoModel(
                            Codigo=id_contrato,
                            Descripcion=descripcion
                        ),
                        Entidad=cached_data["nombre_entidad"],
                        Monto=str(cached_data["valor_contrato"]),
                        FechaInicio=cached_data["fecha_inicio"],
                        NivelRiesgo=cached_data["nivel_riesgo"],
                        Anomalia=cached_data["anomalia"]
                    ))
            
            if len(contratos_mapeados) == len(ids_contratos):
                print(f"✅ Todos los contratos recuperados del caché ({len(contratos_mapeados)})")
                return (
                    stats_cached["total_contratos"],
                    stats_cached["monto_total_cop"],
                    stats_cached["contratos_alto_riesgo"],
                    contratos_mapeados
                )
            else:
                print(f"⚠️ Caché parcial: {len(contratos_mapeados)}/{len(ids_contratos)} contratos")
                print(f"   Procediendo con análisis completo...")
        
        # ==================== ANÁLISIS COMPLETO (Sin caché o caché incompleto) ====================
        print(f"\n📊 ANÁLISIS DE MUESTRA RÁPIDA:")
        print(f"   Modo: Solo {return_limit} contratos más recientes")
        print(f"   Orden: Fecha de inicio DESC")
        print(f"   Análisis: ML sin LLM (rápido)\n")

        # Obtener solo los primeros return_limit contratos
        data_params = {
            "$limit": return_limit,
            "$order": "fecha_de_inicio_del_contrato DESC"
        }
        if where_final:
            data_params["$where"] = where_final
            
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

        # Mapear contratos con análisis real del motor
        contratos_mapeados = []
        contratos_alto_riesgo_reales = 0
        
        try:
            motor = cls._obtener_motor()
            print(f"✓ Motor ML obtenido, analizando {len(data)} contratos (sin LLM para rapidez)...")
        except Exception as e:
            print(f"❌ Error obteniendo motor: {e}")
            raise
        
        for idx, contrato in enumerate(data, 1):
            descripcion_original = contrato.get("objeto_del_contrato", "")
            descripcion_estandarizada = estandarizar_texto(descripcion_original)
            
            # Validación adicional de calidad (por si la API devuelve datos inválidos)
            valor = float(contrato.get("valor_del_contrato", 0))
            fecha_inicio = contrato.get("fecha_de_inicio_del_contrato", "")
            
            # Skip contratos que no pasaron filtros pero llegaron igual
            if valor <= 0 or valor > 50000000000:
                print(f"   ⚠️ Omitido [{idx}/{len(data)}]: Valor inválido (${valor:,.0f})")
                continue
            
            if not descripcion_original or len(descripcion_original) <= 10:
                print(f"   ⚠️ Omitido [{idx}/{len(data)}]: Descripción vacía o muy corta")
                continue
            
            # Preparar datos y ejecutar análisis (solo ML, sin LLM)
            try:
                datos_motor = cls._preparar_datos_para_motor(contrato)
                resultado_ml = motor.analizar_contrato_ml_solo(datos_motor)
                
                # Extraer métricas del análisis
                metadata = resultado_ml.get("Meta_Data", {})
                score = metadata.get("Score", 0.0)  # 0.0 a 1.0
                nivel = metadata.get("Riesgo", "BAJO")  # CRÍTICO, ALTO, BAJO
                
                # Convertir score a porcentaje (0-100)
                anomalia_porcentaje = round(score * 100, 2)
                
                # Mapear nivel de riesgo
                nivel_riesgo = cls._mapear_nivel_riesgo(nivel)
                
                # Contar contratos de alto riesgo reales
                if nivel_riesgo == NivelRiesgo.ALTO:
                    contratos_alto_riesgo_reales += 1
                
                print(f"   ✓ [{idx}/{len(data)}] {contrato.get('id_contrato', 'N/A')}: {anomalia_porcentaje}% ({nivel})")
                
            except Exception as e:
                print(f"   ❌ Error: {contrato.get('id_contrato', 'N/A')}: {str(e)[:100]}")
                # Fallback a valores por defecto si falla el análisis
                anomalia_porcentaje = 0.0
                nivel_riesgo = NivelRiesgo.SIN_ANALISIS
            
            contratos_mapeados.append(ContratoDetalleModel(
                Contrato=ContratoInfoModel(
                    Codigo=contrato.get("id_contrato", ""),
                    Descripcion=descripcion_estandarizada
                ),
                Entidad=contrato.get("nombre_entidad", ""),
                Monto=contrato.get("valor_del_contrato", "0"),
                FechaInicio=contrato.get("fecha_de_inicio_del_contrato"),
                NivelRiesgo=nivel_riesgo,
                Anomalia=anomalia_porcentaje
            ))
        
        # Calcular estadísticas de la muestra
        total_analizados = len(contratos_mapeados)
        porcentaje_alto_riesgo = (contratos_alto_riesgo_reales / total_analizados * 100) if total_analizados > 0 else 0
        
        # Calcular monto total de la muestra
        monto_total = sum(
            float(c.Monto.replace(",", "")) if isinstance(c.Monto, str) else float(c.Monto) 
            for c in contratos_mapeados 
            if c.Monto
        )
        
        print(f"\n📈 ESTADÍSTICAS DE MUESTRA ({return_limit} contratos):")
        print(f"   Total contratos analizados: {total_analizados:,}")
        print(f"   Contratos alto riesgo: {contratos_alto_riesgo_reales:,}")
        print(f"   Porcentaje alto riesgo: {porcentaje_alto_riesgo:.2f}%")
        print(f"   Monto total muestra: ${monto_total:,.2f} COP")
        
        # ==================== GUARDAR EN CACHÉ ====================
        if cache_service.is_enabled:
            print(f"\n💾 Guardando resultados en caché...")
            
            # Preparar datos para batch insert de análisis ligero
            analisis_batch = []
            for contrato_detail in contratos_mapeados:
                analisis_batch.append({
                    "id_contrato": contrato_detail.Contrato.Codigo,
                    "nombre_entidad": contrato_detail.Entidad,
                    "valor_contrato": float(contrato_detail.Monto),
                    "fecha_inicio": contrato_detail.FechaInicio,
                    "nivel_riesgo": contrato_detail.NivelRiesgo.value,
                    "anomalia": contrato_detail.Anomalia,
                    "score_isolation_forest": None,  # Podemos extraer del resultado si lo guardamos
                    "score_nlp_embeddings": None
                })
            
            # Guardar análisis ligero en batch
            cache_service.save_analisis_ligero_batch(analisis_batch)
            
            # Calcular contratos por nivel de riesgo
            contratos_medio = sum(1 for c in contratos_mapeados if c.NivelRiesgo == NivelRiesgo.MEDIO)
            contratos_bajo = sum(1 for c in contratos_mapeados if c.NivelRiesgo == NivelRiesgo.BAJO)
            
            # Guardar estadísticas globales
            cache_service.save_estadisticas(
                filtro_hash=filtro_hash,
                filtro_descripcion=where_clause[:200] if where_clause else "Sin filtros",
                total_contratos=total_analizados,
                contratos_alto_riesgo=contratos_alto_riesgo_reales,
                contratos_medio_riesgo=contratos_medio,
                contratos_bajo_riesgo=contratos_bajo,
                porcentaje_alto_riesgo=porcentaje_alto_riesgo,
                monto_total_cop=monto_total
            )
            
            print(f"✅ Caché actualizado: {len(analisis_batch)} contratos + estadísticas")
        
        print(f"\n✅ Análisis completado. Devolviendo primeros {min(return_limit, len(contratos_mapeados))} contratos\n")

        # Devolver solo los primeros return_limit contratos (ya ordenados por fecha DESC)
        contratos_a_devolver = contratos_mapeados[:return_limit]
        
        return total_analizados, monto_total, contratos_alto_riesgo_reales, contratos_a_devolver

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
            
        Raises:
            HTTPException: Si el contrato tiene datos inválidos
        """
        # Validar calidad de datos del contrato
        valor = float(contrato.get("valor_del_contrato", 0))
        descripcion = contrato.get("objeto_del_contrato", "")
        fecha_inicio = contrato.get("fecha_de_inicio_del_contrato", "")
        
        # Validaciones
        if valor <= 0 or valor > 50000000000:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Valor del contrato inválido",
                    "valor": valor,
                    "message": f"El contrato tiene un valor inválido: ${valor:,.0f} COP. Debe estar entre $1 y $50,000,000,000"
                }
            )
        
        if not descripcion or len(descripcion) <= 10:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Descripción del contrato inválida",
                    "message": "El contrato no tiene una descripción válida o es demasiado corta"
                }
            )
        
        # Validar fecha (año entre 2010 y 2026)
        if fecha_inicio:
            try:
                anio = int(fecha_inicio[:4])
                if anio < 2010 or anio > 2026:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Fecha de inicio inválida",
                            "fecha": fecha_inicio,
                            "message": f"La fecha de inicio ({fecha_inicio}) está fuera del rango válido (2010-2026)"
                        }
                    )
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Formato de fecha inválido",
                        "fecha": fecha_inicio,
                        "message": "La fecha de inicio del contrato tiene un formato inválido"
                    }
                )
        
        # ==================== VERIFICAR CACHÉ ====================
        cached_detallado = cache_service.get_analisis_detallado(contract_id)
        
        if cached_detallado and cache_service.is_enabled:
            print(f"✅ Análisis detallado recuperado del caché: {contract_id}")
            
            # Reconstruir objetos desde caché
            descripcion_estandarizada = estandarizar_texto(contrato.get("objeto_del_contrato", ""))
            monto = contrato.get("valor_del_contrato", "0")
            fecha_inicio = contrato.get("fecha_de_inicio_del_contrato")
            
            # Mapear nivel de riesgo desde caché
            nivel_riesgo_cached = cached_detallado.get("meta_data", {}).get("Riesgo", "BAJO")
            nivel_riesgo = cls._mapear_nivel_riesgo(nivel_riesgo_cached)
            
            # Construir SHAP values desde caché
            shap_values = []
            try:
                cached_shap = cached_detallado.get("shap_values", [])
                logger.debug(f"Reconstruyendo {len(cached_shap)} SHAP values desde caché")
                
                for sv in cached_shap:
                    if isinstance(sv, dict):
                        # Validar campos requeridos
                        variable = sv.get("variable", "unknown")
                        valor = sv.get("valor", 0.0)
                        
                        shap_values.append(ShapValueModel(
                            variable=str(variable),
                            value=float(valor),
                            description=sv.get("description", f"Variable: {variable}"),
                            actualValue=sv.get("actualValue", "Desde caché")
                        ))
                    else:
                        logger.warning(f"SHAP value inválido en caché: {sv}")
                        
            except Exception as e:
                logger.error(f"Error reconstruyendo SHAP values desde caché: {e}")
                shap_values = []
            
            # Construir modelos de respuesta
            contract_detail = ContractDetailModel(
                id=contract_id,
                codigo=contrato.get("id_contrato", contract_id),
                descripcion=descripcion_estandarizada,
                entidad=contrato.get("nombre_entidad", "Entidad no especificada"),
                monto=str(monto),
                fechaInicio=fecha_inicio,
                nivelRiesgo=nivel_riesgo,
                anomalia=round(cached_detallado.get("score_final", 0) * 100, 2)
            )
            
            analysis = AnalysisModel(
                contractId=contract_id,
                resumenEjecutivo=cached_detallado.get("resumen_ejecutivo", "Análisis recuperado desde caché"),
                factoresPrincipales=cached_detallado.get("factores_principales", ["Datos desde caché"]),
                recomendaciones=cached_detallado.get("recomendaciones", ["Verificar datos actualizados"]),
                shapValues=shap_values,
                probabilidadBase=round(cached_detallado.get("score_final", 0) * 80, 1),
                confianza=85.0,  # Confianza del caché
                fechaAnalisis=cached_detallado.get("fecha_analisis", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
            )
            
            return contract_detail, analysis
        
        # ==================== ANÁLISIS COMPLETO (Sin caché) ====================
        
        # Procesar datos del contrato
        descripcion_original = contrato.get("objeto_del_contrato", "Sin descripción")
        descripcion_estandarizada = estandarizar_texto(descripcion_original)
        
        monto = contrato.get("valor_del_contrato", "0")
        fecha_inicio = contrato.get("fecha_de_inicio_del_contrato")
        
        # ============================================
        # ANÁLISIS REAL CON MOTOR DE IA
        # ============================================
        logger.info(f"\n{'='*80}")
        logger.info(f"INICIANDO ANÁLISIS DE CONTRATO: {contract_id}")
        logger.info(f"{'='*80}")
        
        try:
            # Obtener instancia del motor
            motor = cls._obtener_motor()
            logger.info(f"✅ Motor obtenido - LLM disponible: {motor.usar_llm}")
            
            # Preparar datos para el motor
            logger.info("📊 Preparando datos del contrato...")
            datos_motor = cls._preparar_datos_para_motor(contrato)
            
            # Ejecutar análisis completo con ML + LLM
            logger.info("🧠 Ejecutando análisis completo con motor RadarColInferencia (ML + LLM)...")
            logger.info(f"   Parámetros: incluir_llm=True, motor.usar_llm={motor.usar_llm}")
            
            resultado_analisis = motor.analizar_contrato(datos_motor, incluir_llm=True)
            
            # LOGUEAR RESPUESTA COMPLETA DEL MOTOR
            logger.info("="*80)
            logger.info("RESPUESTA COMPLETA DEL MOTOR:")
            logger.info("="*80)
            import json
            logger.info(json.dumps(resultado_analisis, indent=2, ensure_ascii=False))
            logger.info("="*80)
            
            # Log del resultado completo
            logger.info("Análisis completado. Procesando resultados...")
            logger.debug(f"📦 Claves en resultado: {list(resultado_analisis.keys())}")
            
            # Extraer resultados del análisis ML + LLM
            meta_data = resultado_analisis["Meta_Data"]
            nivel_riesgo_str = meta_data["Riesgo"]
            anomalia = meta_data["Score"] * 100  # Convertir a porcentaje
            nivel_riesgo = cls._mapear_nivel_riesgo(nivel_riesgo_str)
            
            logger.info(f"Nivel de Riesgo Detectado: {nivel_riesgo_str} ({anomalia:.1f}%)")
            
            # Extraer análisis LLM (si está disponible)
            analisis_llm = resultado_analisis.get("Analisis_LLM", {})
            logger.info(f"🔍 Análisis LLM presente: {bool(analisis_llm)}")
            
            if analisis_llm:
                logger.info(f"   Claves LLM: {list(analisis_llm.keys())}")
                resumen_llm = analisis_llm.get("resumen", "")
                logger.info(f"   Longitud resumen: {len(resumen_llm)} chars")
                logger.info(f"   Extracto resumen: {resumen_llm[:100]}...")
            
            resumen_ejecutivo = analisis_llm.get("resumen", "Análisis ML completado")
            factores_principales = analisis_llm.get("factores", [])
            recomendaciones = analisis_llm.get("recomendaciones", [])
            detalle_shap = resultado_analisis.get("Detalle_SHAP", [])
            
            logger.info(f"Factores principales encontrados: {len(factores_principales)}")
            logger.info(f"Recomendaciones generadas: {len(recomendaciones)}")
            logger.info(f"Valores SHAP disponibles: {len(detalle_shap)}")
            
            if detalle_shap:
                logger.debug("Detalle SHAP:")
                for item in detalle_shap[:3]:  # Mostrar solo los primeros 3
                    logger.debug(f"   • {item.get('variable', 'N/A')}: {item.get('valor', 0):.4f}")
            
        except Exception as e:
            # Fallback en caso de error del motor
            logger.error(f"ERROR en motor de análisis: {type(e).__name__}")
            logger.error(f"   Mensaje: {str(e)}")
            logger.error(f"   Contrato ID: {contract_id}")
            logger.warning("Activando modo de contingencia con valores por defecto")
            
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
        logger.debug(f"   Detalle SHAP recibido: {len(detalle_shap)} items")
        
        shap_values = []
        try:
            if detalle_shap and isinstance(detalle_shap, list):
                shap_values = cls._construir_shap_values(detalle_shap, contrato)
            else:
                logger.warning(f"Detalle SHAP inválido: {type(detalle_shap)}")
        except Exception as e:
            logger.error(f"Error construyendo SHAP values: {e}")
            logger.error(f"   Tipo detalle_shap: {type(detalle_shap)}")
            logger.error(f"   Contenido detalle_shap: {detalle_shap}")
            shap_values = []
            
        logger.info(f"✅ SHAP values construidos: {len(shap_values)} variables")
        
        if shap_values:
            logger.debug("Variables SHAP principales:")
            for sv in shap_values[:3]:
                logger.debug(f"   • {sv.variable}: {sv.value} ({sv.description})")
        else:
            logger.warning("No se generaron valores SHAP")
        
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
        logger.info(f"ANÁLISIS COMPLETADO EXITOSAMENTE")
        logger.info(f"   Contrato: {contract_id}")
        logger.info(f"   Nivel Riesgo: {nivel_riesgo.value}")
        logger.info(f"   Anomalía: {anomalia:.1f}%")
        logger.info(f"   SHAP Values: {len(shap_values)}")
        logger.info(f"{'='*80}\n")
        
        # ==================== GUARDAR EN CACHÉ ====================
        if cache_service.is_enabled:
            print(f"💾 Guardando análisis detallado en caché: {contract_id}")
            
            try:
                # Guardar análisis detallado
                cache_service.save_analisis_detallado(
                    id_contrato=contract_id,
                    resumen_ejecutivo=resumen_ejecutivo,
                    factores_principales=factores_principales,
                    recomendaciones=recomendaciones,
                    shap_values=[
                        {
                            "variable": sv.variable,
                            "valor": sv.value,
                            "description": sv.description,
                            "actualValue": sv.actualValue
                        } for sv in shap_values
                    ],
                    score_final=anomalia / 100.0,  # Convertir de % a 0-1
                    score_isolation_forest=resultado_analisis.get("Meta_Data", {}).get("Score", 0),
                    score_nlp_embeddings=0.0,  # Extraer si está disponible
                    isolation_forest_raw=resultado_analisis.get("Meta_Data", {}).get("Score", 0),
                    distancia_semantica=0.0,  # Extraer si está disponible
                    meta_data=resultado_analisis.get("Meta_Data", {}),
                    duracion_analisis_ms=0  # Podemos medir esto si queremos
                )
                
                # Asegurar que también exista análisis ligero
                cached_ligero = cache_service.get_analisis_ligero(contract_id)
                if not cached_ligero:
                    cache_service.save_analisis_ligero(
                        id_contrato=contract_id,
                        nombre_entidad=contrato.get("nombre_entidad", ""),
                        valor_contrato=float(monto),
                        fecha_inicio=fecha_inicio,
                        nivel_riesgo=nivel_riesgo.value,
                        anomalia=anomalia,
                        score_isolation_forest=resultado_analisis.get("Meta_Data", {}).get("Score", 0),
                        score_nlp_embeddings=0.0
                    )
                    print(f"   + Análisis ligero también guardado")
                
                print(f"✅ Análisis guardado en caché correctamente")
            except Exception as e:
                print(f"⚠️ Error guardando en caché: {e}")
        
        return contract_data, analysis_data
