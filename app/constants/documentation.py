"""
Constantes de documentación para la API.
"""

# =====================================
# Metadata de la API
# =====================================
API_TITLE = "API de Análisis de Contratos Gubernamentales"
API_VERSION = "1.0.0"
API_DESCRIPTION = """API para el análisis y consulta de contratos del sector público colombiano.

## Funcionalidades

- **Consulta de contratos**: Obtén información detallada de contratos gubernamentales
- **Filtrado avanzado**: Filtra por fecha, valor, entidad e ID específico
- **Análisis de riesgo**: Evaluación automática de niveles de riesgo y anomalías
- **Análisis detallado**: Explicabilidad con valores SHAP y recomendaciones
- **Métricas agregadas**: Estadísticas totales y análisis de alto nivel

## Fuente de Datos

Los datos provienen de **SECOP II** (datos.gov.co), la plataforma oficial de contratación pública de Colombia.

## Campos Simulados

- `nivelRiesgo`: Algoritmo de evaluación de riesgo (simulado)
- `anomalia`: Detección de patrones anómalos (simulado)
- `contratosAltoRiesgo`: Porcentaje basado en análisis estadístico (simulado)
- `shapValues`: Explicabilidad del modelo ML (simulado)
- `recomendaciones`: Basadas en análisis de riesgo (simulado)
"""

API_TERMS_OF_SERVICE = "https://www.datos.gov.co/"
API_CONTACT = {
    "name": "Equipo de Análisis de Contratos",
    "email": "contacto@ejemplo.com",
}
API_LICENSE_INFO = {
    "name": "Open Data License",
    "url": "https://www.datos.gov.co/",
}

# =====================================
# Descripciones de Endpoints
# =====================================
CONTRATOS_DESCRIPTION = """Obtiene una lista de contratos gubernamentales con capacidades de filtrado avanzado y análisis de riesgo.

Este endpoint permite:
- Filtrar contratos por rango de fechas, valores monetarios, entidad contratante e ID específico
- Obtener métricas agregadas (total de contratos, monto total, contratos de alto riesgo)
- Análisis automático de niveles de riesgo y detección de anomalías
- Formateo profesional de descripciones de contratos

**Filtros disponibles:**
- `limit`: Número máximo de contratos a retornar (1-100)
- `fecha_desde` / `fecha_hasta`: Rango de fechas de inicio del contrato
- `valor_minimo` / `valor_maximo`: Rango de valores monetarios
- `nombre_contrato`: Búsqueda por nombre de la entidad contratante
- `id_contrato`: Búsqueda por ID específico de contrato

**Datos retornados:**
- Metadata con fuente de datos y campos simulados
- Total de contratos analizados
- Número de contratos de alto riesgo
- Monto total en COP
- Lista detallada de contratos con información completa
"""

ANALISIS_DESCRIPTION = """Obtiene el análisis detallado con IA de un contrato específico.

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
🔬 Los datos del contrato son reales de datos.gov.co. El análisis (SHAP values, recomendaciones) 
está mockeado hasta conectar con el modelo ML real.
"""

HEALTH_CHECK_DESCRIPTION = """Endpoint de health check ligero para monitoring y keep-alive.

**Uso recomendado:**
- Configurar en UptimeRobot (https://uptimerobot.com) con ping cada 5 minutos
- Configurar en cron-job.org con ejecución cada 5 minutos
- Usar en CI/CD para verificar disponibilidad

Este endpoint mantiene el servicio activo en Render evitando el "cold start".
"""
