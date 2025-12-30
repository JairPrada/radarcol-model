# Documentación Técnica - Sistema de Detección de Anomalías en Contratos

## 📋 Tabla de Contenidos

1. [Variables de Análisis](#variables-de-análisis)
2. [Modelos de Machine Learning](#modelos-de-machine-learning)
3. [Prompt del LLM](#prompt-del-llm)
4. [Proceso de Detección](#proceso-de-detección)
5. [Interpretación de Resultados](#interpretación-de-resultados)

---

## 🔍 Variables de Análisis

El sistema utiliza **9 variables principales** para detectar anomalías en contratos gubernamentales:

### 1. **Z-Score Valor**
- **Descripción**: Desviación del monto del contrato respecto al promedio histórico de la entidad
- **Cálculo**: `(valor - media_entidad) / desviacion_estandar_entidad`
- **Interpretación**:
  - `Z > 3`: Monto crítico (muy por encima del promedio)
  - `2 < Z < 3`: Monto alto
  - `-1 < Z < 2`: Monto normal
- **Impacto**: Variable más importante para detectar sobrecostos

### 2. **Valor Logaritmo**
- **Descripción**: Escala logarítmica del valor del contrato
- **Cálculo**: `log(valor + 1)`
- **Propósito**: Normalizar valores extremos para el modelo ML

### 3. **Costo por Caracter**
- **Descripción**: Ratio entre el monto y la complejidad de la descripción
- **Cálculo**: `valor / longitud_descripcion`
- **Interpretación**: Detecta contratos con alto valor pero descripciones simples (posible fraude)

### 4. **Índice Dependencia Proveedor**
- **Descripción**: Nivel de concentración de contratos con proveedores específicos
- **Rango**: `0.0 - 1.0`
- **Interpretación**: Valores altos indican posible direccionamiento de contratos

### 5. **Porcentaje Tiempo Adicionado**
- **Descripción**: Extensión del plazo original del contrato
- **Cálculo**: `(tiempo_adicionado / duracion_original) * 100`
- **Interpretación**: Valores altos sugieren mala planificación o modificaciones sospechosas

### 6. **Duración en Días**
- **Descripción**: Plazo de ejecución del contrato
- **Interpretación**: 
  - Duraciones muy cortas + alto valor = sospechoso
  - Duraciones muy largas pueden indicar falta de control

### 7. **Días tras Firma**
- **Descripción**: Tiempo transcurrido desde la firma del contrato
- **Propósito**: Contexto temporal para el análisis

### 8. **Año de Firma**
- **Descripción**: Año en que se firmó el contrato
- **Propósito**: Detectar patrones temporales (ej: contratos al final del año fiscal)

### 9. **Mes de Firma**
- **Descripción**: Mes en que se firmó el contrato
- **Rango**: `1-12`
- **Interpretación**: Meses específicos pueden tener mayor riesgo (ej: diciembre)

---

## 🤖 Modelos de Machine Learning

El sistema utiliza un **ensemble de 2 modelos** para calcular el riesgo final:

### Modelo 1: IsolationForest (50% del score)

**Tipo**: Detección de anomalías no supervisada

**Entrada**: Las 9 variables numéricas

**Salida**: Score de anomalía normalizado entre 0 y 1
- `0`: Contrato normal
- `0.5`: Contrato con algunas características inusuales
- `1.0`: Contrato altamente anómalo

**Cálculo**:
```python
score_raw = iso_forest.decision_function(features)
risk_ml = 1 - ((score_raw - (-0.5)) / (0.5 - (-0.5)))
risk_ml = clip(risk_ml, 0, 1)

# Ajuste crítico:
if Z_Score > 3:
    risk_ml = 1.0  # Override automático para valores extremos
```

**Explicabilidad**: SHAP (SHapley Additive exPlanations)
- Identifica qué variables contribuyen más al score de riesgo
- Genera valores de importancia para cada variable
- Permite visualización de factores clave

### Modelo 2: Análisis Semántico NLP (50% del score)

**Tipo**: Embeddings textuales con Sentence Transformers

**Modelo**: `hiiamsid/sentence_similarity_spanish_es`

**Entrada**: Descripción del objeto del contrato (primeros 200 caracteres)

**Proceso**:
1. Convertir descripción a vector embedding (768 dimensiones)
2. Calcular distancia euclidiana respecto al centroide semántico
3. Normalizar distancia a score de riesgo

**Cálculo**:
```python
embedding = model_nlp.encode(descripcion[:200])
distancia = norm(embedding - centroide)
risk_nlp = clip(distancia / 1.2, 0, 1)
```

**Interpretación**:
- `risk_nlp < 0.4`: Descripción típica/normal
- `0.4 < risk_nlp < 0.6`: Descripción moderadamente diferente
- `risk_nlp > 0.6`: Descripción muy inusual

### Score Final (Ensemble)

```python
score_final = (risk_ml * 0.5) + (risk_nlp * 0.5)
```

**Clasificación de Riesgo**:
- `score_final > 0.8`: **CRÍTICO** (prioridad máxima de auditoría)
- `0.5 < score_final ≤ 0.8`: **ALTO** (requiere revisión detallada)
- `score_final ≤ 0.5`: **BAJO** (contratos normales)

---

## 💬 Prompt del LLM (Groq - LLaMA 3.1 8B Instant)

### Configuración del Sistema

**Modelo**: `llama-3.1-8b-instant`
- **Gratuito**: 30 req/min, 14,400 req/día
- **Temperature**: 0.3 (respuestas determinísticas)
- **Max tokens**: 800
- **Formato**: JSON obligatorio

### System Prompt

```text
Eres un auditor forense experto en contratación pública. 
Respondes SOLO con JSON válido.
```

### User Prompt Completo

```text
Eres un Auditor Forense que explica hallazgos a personas SIN conocimientos técnicos 
(alcaldes, concejales, ciudadanos).

DATOS DEL CONTRATO:
- ID: {ID_Contrato}
- Descripción: "{Objeto_Contrato}"
- Valor: ${Valor:,.0f} COP (${Valor_Millones:.1f} millones)
- Entidad: {Nit_Entidad}
- Duración: {Duracion_Dias} días ({Duracion_Meses:.1f} meses aprox.)

RESULTADO DE LOS MODELOS DE ANÁLISIS:

1. DETECTOR DE ANOMALÍAS (IsolationForest): {score_ml:.2%}
   Interpretación: Este modelo detectó un nivel {ALTO|MEDIO|BAJO} de anomalía 
   en los valores numéricos del contrato.
   {Texto_Interpretación_ML}

2. ANÁLISIS SEMÁNTICO (Embeddings): {score_nlp:.2%}
   Interpretación: La descripción del contrato es {muy diferente|moderadamente diferente|similar} 
   respecto a contratos habituales.
   {Texto_Interpretación_NLP}

3. Z-SCORE DEL VALOR: {Z_Score:.2f}
   {Mensaje_Crítico_o_Normal}

4. NIVEL DE RIESGO FINAL: {CRÍTICO|ALTO|BAJO} ({riesgo:.0%})

ANÁLISIS DE FACTORES CLAVE (Top 5 SHAP):
   1. {Variable_1}: {Peso} ({intensidad} {aumenta|disminuye} el riesgo)
   2. {Variable_2}: {Peso} (...)
   ...

INSTRUCCIONES CRÍTICAS:
1. USA LENGUAJE SIMPLE Y COTIDIANO - Evita términos técnicos como 
   "Z-Score", "embeddings", "SHAP", "IsolationForest"
2. USA ANALOGÍAS Y COMPARACIONES - Ejemplo: "como si compraras un pan por el precio de 10 panes"
3. EXPLICA EL "POR QUÉ ES ANÓMALO" en términos que cualquier persona entienda
4. FACTORES: Describe cada factor clave en lenguaje sencillo, explicando su impacto real
5. RECOMENDACIONES: Acciones concretas y comprensibles para funcionarios no técnicos
6. Los arrays "factores" y "recomendaciones" DEBEN contener SOLO STRINGS SIMPLES

EJEMPLOS DE LENGUAJE SIMPLE:
❌ MAL: "El Z-Score de 3.5 indica una desviación estándar significativa"
✅ BIEN: "El precio de este contrato es 3.5 veces más alto que el promedio que 
         esta entidad suele pagar por contratos similares"

❌ MAL: "El score del IsolationForest es 0.82"
✅ BIEN: "Nuestro sistema de detección de anomalías encontró que este contrato 
         tiene características muy distintas al 82% de contratos normales"

FORMATO JSON REQUERIDO:
{
    "resumen": "Explicación clara y directa de por qué este contrato es sospechoso (o normal). 
                Usa lenguaje simple, menciona cifras concretas en millones de pesos, 
                compara con promedios. Máximo 3-4 oraciones cortas.",
    
    "factores": [
        "El precio del contrato es [X] veces más alto que el promedio habitual de esta entidad, 
         lo que sugiere posible sobrecosto",
        "La relación entre el precio y la complejidad del trabajo es inusual: se está pagando 
         mucho dinero por una descripción de trabajo relativamente simple",
        "La duración del contrato combinada con el monto resulta en un costo diario muy elevado 
         comparado con contratos similares",
        "[Otro factor en lenguaje simple]"
    ],
    
    "recomendaciones": [
        "Solicitar una justificación detallada de por qué este contrato cuesta [X] millones 
         más que el promedio de contratos similares",
        "Comparar este contrato con al menos 3 contratos similares ejecutados por la misma entidad 
         en los últimos 2 años",
        "Revisar si existe un estudio de mercado que respalde el precio contratado",
        "[Otra acción concreta y entendible]"
    ]
}

RECUERDA: Tu audiencia son ciudadanos, periodistas, y funcionarios NO técnicos. 
Sé claro, directo y evita jerga técnica.
```

### Reglas de Validación Post-Procesamiento

El sistema valida y convierte automáticamente la respuesta del LLM:

1. **Si `factores` contiene objetos** → Extrae campo `descripcion` o concatena valores
2. **Si `recomendaciones` contiene objetos** → Extrae campo `accion` o concatena valores
3. **Asegura arrays de strings simples** para compatibilidad con frontend

---

## 🔄 Proceso de Detección (Pipeline Completo)

### Paso 1: Preprocesamiento
```python
1. Extraer datos del contrato (valor, descripción, NIT, duración)
2. Calcular estadísticas históricas de la entidad (media, desviación)
3. Generar 9 features numéricas
4. Normalizar valores para los modelos
```

### Paso 2: Scoring ML
```python
1. Ejecutar IsolationForest → risk_ml (0-1)
2. Codificar descripción con NLP → embedding
3. Calcular distancia semántica → risk_nlp (0-1)
4. Ensemble: score_final = (risk_ml + risk_nlp) / 2
```

### Paso 3: Explicabilidad (SHAP)
```python
1. Calcular valores SHAP para las 9 variables
2. Identificar variable principal (max |SHAP value|)
3. Generar lista ordenada de factores clave
4. Crear objeto JSON para gráficas frontend
```

### Paso 4: Generación de Análisis (LLM)
```python
1. Construir prompt con datos + scores + SHAP
2. Enviar a Groq API (con retry automático)
3. Parsear respuesta JSON
4. Validar y limpiar factores/recomendaciones
5. Retornar análisis en lenguaje natural
```

### Paso 5: Respuesta Final
```python
{
    "ID": "CO1.PCCNTR.XXXXX",
    "Resumen_Ejecutivo": "...",
    "Factores_Principales": [...],
    "Recomendaciones_Auditor": [...],
    "Detalle_SHAP": [
        {"variable": "z_score_valor", "peso": -4.02},
        {"variable": "anio_firma", "peso": -0.7},
        ...
    ],
    "Meta_Data": {
        "Riesgo": "CRÍTICO|ALTO|BAJO",
        "Score": 0.88,
        "Score_IsolationForest": 0.92,
        "Score_NLP_Embeddings": 0.84,
        "IsolationForest_Raw": -0.123,
        "Distancia_Semantica": 0.756,
        "Pesos_Ensemble": {"ML": 0.5, "NLP": 0.5},
        "Modelo_NLP": "hiiamsid/sentence_similarity_spanish_es"
    }
}
```

---

## 📊 Interpretación de Resultados

### Rangos de Riesgo

| Score Final | Nivel | Anomalía % | Acción Recomendada |
|-------------|-------|------------|-------------------|
| 0.8 - 1.0 | CRÍTICO | 80-100% | Auditoría inmediata, revisión legal |
| 0.5 - 0.8 | ALTO | 50-80% | Revisión detallada, solicitar justificación |
| 0.0 - 0.5 | BAJO | 0-50% | Monitoreo estándar |

### Factores de Riesgo Comunes

**Sobrecosto Extremo (Z-Score > 3)**
- Indica que el contrato cuesta significativamente más que el promedio histórico
- Puede sugerir corrupción, cartelización o mala negociación

**Descripción Atípica (risk_nlp > 0.6)**
- El texto del contrato es muy diferente a contratos normales
- Puede indicar lenguaje vago, objeto mal definido o intento de ocultar información

**Alto Costo por Carácter**
- Monto elevado con descripción muy simple
- Sugiere posible sobrefacturación o falta de especificaciones técnicas

**Duración Anómala**
- Duraciones muy cortas con altos valores
- Duraciones muy largas sin justificación clara

### Señales de Alerta Múltiples

Cuando un contrato cumple **3 o más** de estos criterios, la probabilidad de irregularidad aumenta significativamente:

1. ✓ Z-Score > 2.5
2. ✓ risk_nlp > 0.5
3. ✓ Costo por carácter en percentil 90+
4. ✓ Índice dependencia proveedor > 0.7
5. ✓ Duración < 30 días con valor > 100M COP

---

## 🔧 Configuración y Ajustes

### Variables de Entorno

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxx          # API key de Groq
RUTA_ARTEFACTOS=data/artifacts           # Ruta a modelos ML
BASE_URL=https://www.datos.gov.co/...   # API de datos gubernamentales
```

### Artefactos Requeridos

1. **modelo_isoforest.pkl**: Modelo IsolationForest entrenado
2. **centroide_semantico.npy**: Vector centroide de embeddings normales
3. **stats_entidades.json**: Estadísticas históricas por entidad
4. **shap_explainer.pkl**: Explainer SHAP pre-calculado

### Umbrales Configurables

```python
# En analyzer.py
UMBRAL_CRITICO = 0.8      # Score para nivel CRÍTICO
UMBRAL_ALTO = 0.5         # Score para nivel ALTO
PESO_ML = 0.5             # Peso IsolationForest en ensemble
PESO_NLP = 0.5            # Peso NLP en ensemble
Z_SCORE_CRITICO = 3.0     # Z-Score para override automático
```

---

## 📝 Notas Técnicas

- **Lenguaje**: Python 3.11+
- **Framework**: FastAPI 0.125.0
- **ML**: scikit-learn 1.3.0, SHAP
- **NLP**: sentence-transformers 2.2.2
- **LLM**: Groq API (llama-3.1-8b-instant)
- **Servidor**: Uvicorn (ASGI)

**Autor**: Sistema RadarCol - Detección de Anomalías en Contratación Pública
**Versión**: 2.5
**Última actualización**: Diciembre 2025
