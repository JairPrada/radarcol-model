"""
Servicio de contratos - Lógica de negocio para gestión de contratos.
"""
import requests
import random
from typing import List, Dict, Any
from fastapi import HTTPException

from app.config import BASE_URL
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


class ContractService:
    """Servicio para gestionar operaciones relacionadas con contratos."""
    
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

    @staticmethod
    def generar_analisis_contrato(
        contract_id: str,
        contrato: Dict[str, Any]
    ) -> tuple[ContractDetailModel, AnalysisModel]:
        """Genera análisis detallado de un contrato.
        
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
        
        # Generar análisis de riesgo simulado
        nivel_riesgo = random.choice(list(NivelRiesgo))
        anomalia = round(random.uniform(0, 100), 2)
        
        # Datos del contrato
        contract_data = ContractDetailModel(
            id=contract_id,
            codigo=contrato.get("id_contrato", contract_id),
            descripcion=descripcion_estandarizada,
            entidad=contrato.get("nombre_entidad", "Entidad no especificada"),
            monto=str(monto),
            fechaInicio=fecha_inicio,
            nivelRiesgo=nivel_riesgo,
            anomalia=anomalia
        )
        
        # Calcular duración estimada
        duracion_dias = "N/A"
        if fecha_inicio and contrato.get("plazo_de_ejec_del_contrato"):
            duracion_dias = str(contrato.get("plazo_de_ejec_del_contrato", "N/A"))
        
        # Análisis mockeado con datos dinámicos
        analysis_data = AnalysisModel(
            contractId=contract_id,
            resumenEjecutivo=f"""Este contrato de {contract_data.entidad} presenta un nivel de riesgo {nivel_riesgo.value.lower()} ({anomalia:.1f}% de probabilidad de anomalía) según el análisis del modelo predictivo. El monto del contrato (${monto} COP) ha sido evaluado en relación con contratos similares en el sector.

El análisis identifica varios factores clave que influyen en la evaluación de riesgo. La naturaleza del contrato ({descripcion_estandarizada[:100]}...) y las características específicas de la entidad contratante son elementos considerados en el modelo de predicción.

Se recomienda implementar mecanismos de supervisión acordes al nivel de riesgo identificado y establecer controles periódicos para el seguimiento del contrato. La entidad contratante debe mantener especial atención en los indicadores de cumplimiento y ejecución presupuestal.""",
            
            factoresPrincipales=[
                f"Monto del contrato: ${monto} COP - Factor principal en la evaluación de riesgo",
                f"Entidad contratante: {contract_data.entidad} - Análisis de histórico institucional",
                f"Alcance del contrato: {descripcion_estandarizada[:150]}",
                f"Fecha de inicio programada: {fecha_inicio or 'No especificada'} - Afecta timeline de ejecución",
                "Contexto sectorial y comparativa con contratos similares en la base de datos"
            ],
            
            recomendaciones=[
                f"Establecer comité de supervisión con revisiones {'mensuales' if nivel_riesgo == NivelRiesgo.ALTO else 'trimestrales'} del avance",
                "Implementar sistema de alertas tempranas para detectar desviaciones en cronograma o presupuesto",
                f"{'Solicitar garantías adicionales por el alto nivel de riesgo identificado' if nivel_riesgo == NivelRiesgo.ALTO else 'Mantener garantías estándar según normativa vigente'}",
                "Realizar auditorías técnicas periódicas por parte de un tercero independiente",
                "Establecer cláusulas de cumplimiento claras y mecanismos de penalización proporcionales"
            ],
            
            shapValues=[
                ShapValueModel(
                    variable="monto_contrato",
                    value=15.2,
                    description="Monto del contrato",
                    actualValue=str(monto)
                ),
                ShapValueModel(
                    variable="tipo_contratacion",
                    value=12.3,
                    description="Tipo de contratación",
                    actualValue=contrato.get("tipo_de_contrato", "No especificado")
                ),
                ShapValueModel(
                    variable="duracion_dias",
                    value=10.8,
                    description="Duración en días",
                    actualValue=duracion_dias
                ),
                ShapValueModel(
                    variable="entidad_contratante",
                    value=8.5,
                    description="Entidad contratante",
                    actualValue=contract_data.entidad
                ),
                ShapValueModel(
                    variable="ubicacion_geografica",
                    value=7.2,
                    description="Complejidad de ubicación",
                    actualValue=contrato.get("departamento", "No especificado")
                ),
                ShapValueModel(
                    variable="tipo_obra",
                    value=5.8,
                    description="Naturaleza del contrato",
                    actualValue=descripcion_estandarizada[:50]
                ),
                ShapValueModel(
                    variable="experiencia_contratista",
                    value=-4.3,
                    description="Experiencia del contratista",
                    actualValue="Evaluación pendiente"
                ),
                ShapValueModel(
                    variable="indices_financieros",
                    value=-3.1,
                    description="Indicadores financieros",
                    actualValue="A evaluar"
                ),
                ShapValueModel(
                    variable="certificaciones",
                    value=-2.5,
                    description="Certificaciones de calidad",
                    actualValue="A verificar"
                )
            ],
            
            probabilidadBase=45.0,
            confianza=87.5,
            fechaAnalisis="2025-12-23T10:30:00Z"
        )
        
        return contract_data, analysis_data
