-- ============================================
-- MIGRACIÓN 001: Crear tablas de caché
-- Fecha: 2025-01-01
-- Descripción: Estructura de base de datos para sistema de caché con Turso
-- ============================================

-- Tabla 1: Estadísticas Globales
-- Almacena métricas agregadas por combinación de filtros
CREATE TABLE IF NOT EXISTS estadisticas_globales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filtro_hash TEXT UNIQUE NOT NULL,
    filtro_descripcion TEXT,
    
    -- Métricas
    total_contratos INTEGER NOT NULL,
    contratos_alto_riesgo INTEGER NOT NULL,
    contratos_medio_riesgo INTEGER NOT NULL,
    contratos_bajo_riesgo INTEGER NOT NULL,
    porcentaje_alto_riesgo REAL,
    monto_total_cop REAL NOT NULL,
    
    -- Metadatos
    fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP,
    version_modelo TEXT DEFAULT 'v1.0'
);

-- Índices para estadisticas_globales
CREATE INDEX IF NOT EXISTS idx_filtro_hash ON estadisticas_globales(filtro_hash);
CREATE INDEX IF NOT EXISTS idx_expiracion_stats ON estadisticas_globales(fecha_expiracion);

-- Tabla 2: Análisis Ligero (para endpoint /contratos)
-- Almacena resultados de análisis ML sin LLM
CREATE TABLE IF NOT EXISTS contratos_analisis_ligero (
    id_contrato TEXT PRIMARY KEY,
    
    -- Datos básicos del contrato
    nombre_entidad TEXT,
    valor_contrato REAL,
    fecha_inicio TEXT,
    
    -- Análisis ML (sin LLM)
    nivel_riesgo TEXT NOT NULL,
    anomalia REAL NOT NULL,
    score_isolation_forest REAL,
    score_nlp_embeddings REAL,
    
    -- Metadatos
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP,
    version_modelo TEXT DEFAULT 'v1.0'
);

-- Índices para contratos_analisis_ligero
CREATE INDEX IF NOT EXISTS idx_nivel_riesgo ON contratos_analisis_ligero(nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_anomalia ON contratos_analisis_ligero(anomalia DESC);
CREATE INDEX IF NOT EXISTS idx_fecha_inicio ON contratos_analisis_ligero(fecha_inicio DESC);
CREATE INDEX IF NOT EXISTS idx_expiracion_ligero ON contratos_analisis_ligero(fecha_expiracion);

-- Tabla 3: Análisis Detallado (para endpoint /contratos/{id}/analisis)
-- Almacena análisis completo con ML + LLM + SHAP
CREATE TABLE IF NOT EXISTS contratos_analisis_detallado (
    id_contrato TEXT PRIMARY KEY,
    
    -- Análisis completo (ML + LLM)
    resumen_ejecutivo TEXT,
    factores_principales TEXT,
    recomendaciones TEXT,
    
    -- SHAP Values (explicabilidad)
    shap_values TEXT,
    
    -- Scores detallados
    score_final REAL,
    score_isolation_forest REAL,
    score_nlp_embeddings REAL,
    isolation_forest_raw REAL,
    distancia_semantica REAL,
    
    -- Metadatos adicionales
    meta_data TEXT,
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP,
    duracion_analisis_ms INTEGER,
    uso_llm BOOLEAN DEFAULT 1,
    version_modelo TEXT DEFAULT 'v1.0',
    
    -- Foreign Key (referencia al análisis ligero)
    FOREIGN KEY (id_contrato) REFERENCES contratos_analisis_ligero(id_contrato)
);

-- Índices para contratos_analisis_detallado
CREATE INDEX IF NOT EXISTS idx_expiracion_detallado ON contratos_analisis_detallado(fecha_expiracion);
CREATE INDEX IF NOT EXISTS idx_fecha_analisis ON contratos_analisis_detallado(fecha_analisis DESC);

-- ============================================
-- VERIFICACIÓN
-- ============================================
-- Las siguientes consultas verifican que las tablas se crearon correctamente

-- SELECT name FROM sqlite_master WHERE type='table';
-- SELECT COUNT(*) FROM estadisticas_globales;
-- SELECT COUNT(*) FROM contratos_analisis_ligero;
-- SELECT COUNT(*) FROM contratos_analisis_detallado;
