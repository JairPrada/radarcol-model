# 🧠 Optimización de Memoria - RadarCol API

## 📊 Problema: "Out of Memory (used over 512MB)"

Este documento explica cómo resolver el error de memoria en ambientes con recursos limitados (como Render free tier con 512MB RAM).

---

## 🔍 Diagnóstico del Problema

El motor de análisis RadarCol utiliza varios componentes que consumen memoria:

| Componente | Consumo RAM | ¿Opcional? |
|------------|-------------|------------|
| FastAPI + Uvicorn | ~50-80MB | ❌ No |
| scikit-learn (IsolationForest) | ~30-50MB | ❌ No |
| NumPy + Pandas | ~40-60MB | ❌ No |
| Groq API Client | ~10-20MB | ❌ No |
| **SentenceTransformer (Embeddings)** | **~400-800MB** | ✅ **Sí** |
| SHAP Explainer | ~30-50MB | ✅ Sí |
| **TOTAL (sin embeddings)** | **~200-300MB** | ✅ Funciona en 512MB |
| **TOTAL (con embeddings)** | **~600-1000MB** | ❌ Excede 512MB |

### 💡 Solución: Sistema de Embeddings Opcional

Se implementó un **Feature Toggle** que permite deshabilitar el modelo de embeddings pesado manteniendo la funcionalidad completa del sistema.

---

## ⚙️ Configuración

### Opción 1: Modo Ligero (Recomendado para Free Tier)

**Variables de entorno:**
```env
ENABLE_EMBEDDINGS=false
```

**Características:**
- ✅ Consumo: ~200-300MB RAM
- ✅ Funciona en Render free tier (512MB)
- ✅ Análisis ML (IsolationForest) completo
- ✅ Análisis LLM (Groq) completo
- ⚠️ Sin análisis semántico de texto (score NLP = 0.0)
- ⚠️ Riesgo calculado 100% basado en variables financieras

**Fórmula de riesgo:**
```
Score Final = Score ML (100%)
```

### Opción 2: Modo Completo (Requiere >1GB RAM)

**Variables de entorno:**
```env
ENABLE_EMBEDDINGS=true
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

**Características:**
- ✅ Análisis completo: ML + LLM + Semántica
- ✅ Detecta anomalías en texto del contrato
- ✅ Score semántico por similitud con centroide
- ❌ Consumo: ~600-800MB RAM
- ❌ No funciona en Render free tier

**Fórmula de riesgo:**
```
Score Final = Score ML (70%) + Score NLP (30%)
```

---

## 🎯 Patrones de Diseño Aplicados

### 1. **Feature Toggle Pattern**

Permite activar/desactivar funcionalidades mediante configuración externa sin cambiar código.

**Beneficios:**
- Deployment flexible
- A/B testing
- Rollback instantáneo
- Adaptación a recursos disponibles

**Implementación:**
```python
# En settings.py
ENABLE_EMBEDDINGS = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"

# En analyzer.py
if self.enable_embeddings:
    self.model_nlp = SentenceTransformer(...)
else:
    self.model_nlp = None
    print("⚙️ Embeddings deshabilitados (modo bajo consumo)")
```

### 2. **Strategy Pattern**

Dos estrategias para calcular el score de riesgo:

- **EmbeddingsStrategy**: usa análisis semántico (score NLP)
- **NoEmbeddingsStrategy**: usa solo análisis financiero (score ML)

**Implementación:**
```python
# Cálculo adaptativo de score combinado
if self.model_nlp:
    score_combinado = risk_ml * 0.7 + risk_nlp * 0.3
else:
    score_combinado = risk_ml  # 100% ML
```

### 3. **Graceful Degradation**

El sistema continúa funcionando con capacidades reducidas en lugar de fallar completamente.

**Implementación:**
```python
try:
    self.model_nlp = SentenceTransformer(...)
except Exception as e:
    print(f"⚠️ Error cargando embeddings: {e}")
    self.model_nlp = None
    self.enable_embeddings = False
```

---

## 📈 Comparación de Modos

| Aspecto | Modo Ligero | Modo Completo |
|---------|-------------|---------------|
| **RAM** | ~200-300MB | ~600-800MB |
| **Detección anomalías financieras** | ✅ Completa | ✅ Completa |
| **Análisis LLM (Groq)** | ✅ Completo | ✅ Completo |
| **Análisis semántico texto** | ❌ Deshabilitado | ✅ Habilitado |
| **SHAP explicabilidad** | ✅ Sí | ✅ Sí |
| **Free tier compatible** | ✅ Sí | ❌ No |
| **Precisión detección** | Alta (ML + LLM) | Muy Alta (ML + LLM + NLP) |

---

## 🚀 Despliegue en Render Free Tier

### Configuración Recomendada

```env
# Variables de entorno en Render Dashboard
GROQ_API_KEY=tu_api_key_aqui
ENABLE_EMBEDDINGS=false
CORS_ORIGINS=https://tu-frontend.com
BASE_URL=https://www.datos.gov.co/resource/jbjy-vk9h.json
RUTA_ARTEFACTOS=data/artifacts
```

### Verificación de Memoria

Al iniciar el servicio, verás logs como:

```
⚙️ Inicializando Motor RadarCol (Groq + ML)...
   ✨ Cliente Groq conectado (llama-3.1-8b-instant)
   📁 Intentando cargar desde: data/artifacts
   ✅ Artefactos cargados correctamente
   ✅ SHAP explainer cargado correctamente
   ⚙️ Embeddings deshabilitados (modo bajo consumo de memoria)
   ℹ️  El análisis usará solo ML + LLM (sin score semántico)
🧠 Embeddings habilitados: False
```

---

## 🔧 Troubleshooting

### Problema: Sigue dando error de memoria

**Soluciones adicionales:**

1. **Deshabilitar SHAP (opcional):**
   - Edita `analyzer.py` y comenta la carga de SHAP explainer
   - Ahorra ~30-50MB adicionales

2. **Optimizar requirements.txt:**
   ```txt
   # Usar versiones específicas más ligeras
   scikit-learn==1.3.0  # No usar 1.5.x que es más pesada
   numpy>=1.21.0,<2.0.0  # NumPy 2.x consume más memoria
   ```

3. **Lazy loading de modelos:**
   - Los modelos se cargan solo una vez al iniciar
   - No se recargan en cada request

### Problema: Quiero habilitar embeddings en free tier

**No es posible sin modificaciones mayores:**

- Render free tier = 512MB fijo
- Embeddings + App = ~600-800MB
- Alternativas:
  1. Upgrade a plan pago ($7/mes con 512MB-2GB)
  2. Usar otro proveedor (Railway, Fly.io con más RAM gratuita)
  3. Implementar embeddings como servicio separado

---

## 📚 Referencias de Aprendizaje

### Patrones Aplicados

1. **Feature Toggle:**
   - [Martin Fowler - Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
   - Permite cambios sin deployments

2. **Strategy Pattern:**
   - [Refactoring Guru - Strategy](https://refactoring.guru/design-patterns/strategy)
   - Intercambiar algoritmos en runtime

3. **Graceful Degradation:**
   - [MDN - Graceful Degradation](https://developer.mozilla.org/en-US/docs/Glossary/Graceful_degradation)
   - Fallback automático a funcionalidad reducida

### Optimización de Memoria en Python

- [Python Memory Management](https://realpython.com/python-memory-management/)
- [Optimizing ML Models](https://huggingface.co/docs/transformers/performance)

---

## ✅ Resumen

1. **Problema:** Modelo de embeddings consume >400MB → Excede límite de 512MB
2. **Solución:** Feature Toggle para deshabilitar embeddings
3. **Resultado:** App funcional en 200-300MB (compatible con free tier)
4. **Trade-off:** Sin análisis semántico, pero mantiene detección de anomalías financieras + LLM
5. **Arquitectura:** Limpia, extensible, permite reactivar embeddings en ambientes con más recursos

**Para producción con recursos limitados: `ENABLE_EMBEDDINGS=false`** ✅
