# 🚀 API de Análisis de Contratos Gubernamentales

API FastAPI para el análisis y consulta de contratos del sector público colombiano desde la plataforma SECOP II (datos.gov.co).

## 📋 Características

- ✅ **Consulta de contratos**: Información detallada de contratos gubernamentales
- 🔍 **Filtrado avanzado**: Por fecha, valor, entidad e ID
- 📊 **Análisis de riesgo**: Evaluación de niveles de riesgo y anomalías con ML
- 🤖 **IA Generativa**: Análisis profundo con Groq API (LLaMA 3.1 8B)
- 📈 **Métricas agregadas**: Estadísticas y análisis de alto nivel
- 🔐 **CORS configurado**: Soporte para múltiples orígenes
- 📝 **Logging completo**: Debugging detallado para producción
- ☁️  **Cloud-ready**: Optimizado para Render free tier

## 🛠️ Tecnologías

### Backend & API
- **FastAPI** 0.125.0 - Framework web moderno y rápido
- **Uvicorn** 0.38.0 - Servidor ASGI de alto rendimiento
- **Pydantic** 2.12.3 - Validación de datos con tipos
- **Python-dotenv** 1.0.0 - Gestión de variables de entorno
- **Requests** 2.32.3 - Cliente HTTP

### Motor de Análisis ML + IA
- **Groq API** 0.13.0 - LLM API ultra-rápida (LLaMA 3.1 8B Instant)
- **scikit-learn** 1.3.0 - IsolationForest para detección de anomalías
- **sentence-transformers** 2.2.2 - Embeddings semánticos en español
- **joblib** 1.3.2 - Serialización de modelos
- **numpy** & **pandas** - Procesamiento de datos

## 📁 Estructura del Proyecto

```
backend/
├── app/                          # Paquete principal de la aplicación
│   ├── __init__.py
│   ├── main.py                   # Punto de entrada FastAPI
│   ├── core/                     # Motor de análisis ML/IA
│   │   ├── __init__.py
│   │   └── analyzer.py          # RadarColInferencia (ML + LLM)
│   ├── config/                   # Configuraciones
│   │   ├── __init__.py
│   │   └── settings.py          # Variables de entorno y configuración
│   ├── constants/               # Constantes y documentación
│   │   ├── __init__.py
│   │   └── api_docs.py          # Textos de documentación de la API
│   ├── models/                  # Modelos Pydantic
│   │   ├── __init__.py
│   │   └── schemas.py           # DTOs y modelos de datos
│   ├── middlewares/             # Middlewares personalizados
│   │   ├── __init__.py
│   │   └── logging.py           # Middleware de logging
│   ├── controllers/             # Controladores/Routers
│   │   ├── __init__.py
│   │   ├── contract_controller.py
│   │   └── health_controller.py
│   ├── services/                # Lógica de negocio
│   │   ├── __init__.py
│   │   └── contract_service.py
│   └── utils/                   # Utilidades
│       ├── __init__.py
│       └── text_formatter.py
├── data/
│   └── artifacts/               # Artefactos ML pre-entrenados
│       ├── modelo_isoforest.pkl
│       ├── centroide_semantico.npy
│       ├── stats_entidades.json
│       └── shap_explainer.pkl
├── main.py                      # Entry point para deployment
├── requirements.txt             # Dependencias Python
├── render.yaml                  # Configuración Render
├── Procfile                     # Comando de inicio
├── .env.example                 # Template de variables de entorno
├── DOCUMENTATION.md             # Documentación técnica completa
└── README.md                    # Este archivo
│   ├── services/                # Lógica de negocio
│   │   ├── __init__.py
│   │   └── contract_service.py  # Servicio de contratos
│   ├── controllers/             # Controladores/Rutas
│   │   ├── __init__.py
│   │   ├── health.py            # Endpoints de salud
│   │   └── contracts.py         # Endpoints de contratos
│   └── utils/                   # Utilidades
│       ├── __init__.py
│       └── text_formatter.py    # Funciones de formateo
├── main_entry.py                # Wrapper de compatibilidad
├── requirements.txt             # Dependencias Python
├── .env                         # Variables de entorno (local)
├── .env.example                # Template de variables
├── .gitignore                  # Archivos ignorados por Git
├── README.md                   # Documentación
└── KEEP_ALIVE.md              # Guía de keep-alive
```

### 🎯 Arquitectura

El proyecto sigue una **arquitectura limpia** con separación de responsabilidades:

- **config/**: Configuración centralizada y variables de entorno
- **constants/**: Constantes y textos reutilizables
- **models/**: Modelos de datos con validación Pydantic
- **middlewares/**: Procesamiento de peticiones/respuestas
- **services/**: Lógica de negocio y casos de uso
- **controllers/**: Endpoints y manejo de peticiones HTTP
- **utils/**: Funciones auxiliares y utilidades

## 📦 Instalación Local

### Requisitos Previos

- Python 3.11+
- pip

### Pasos

1. **Clonar el repositorio**

```bash
git clone https://github.com/JairPrada/radarcol-model.git
cd radarcol-model
```

2. **Crear entorno virtual**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Copia el archivo `.env.example` a `.env` y ajusta los valores:

```bash
cp .env.example .env
```

Edita `.env`:

```env
PORT=8000
HOST=0.0.0.0
BASE_URL=https://www.datos.gov.co/resource/jbjy-vk9h.json
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LOG_LEVEL=INFO

# Motor de Análisis IA con Groq (Gratuito)
# Obtén tu API key en: https://console.groq.com/keys
# Free tier: 30 req/min, 14,400 req/día
GROQ_API_KEY=tu_api_key_de_groq_aqui
RUTA_ARTEFACTOS=data/artifacts

# Configuración de Embeddings (Análisis Semántico)
# false = Modo ligero (~200MB) - Recomendado para desarrollo local o free tier
# true = Modo completo (~600MB) - Requiere > 1GB RAM disponible
ENABLE_EMBEDDINGS=false

# Modelo de embeddings (solo si ENABLE_EMBEDDINGS=true)
# Opciones: paraphrase-multilingual-MiniLM-L12-v2 (~120MB, recomendado)
#           hiiamsid/sentence_similarity_spanish_es (~500MB, mejor calidad)
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

5. **Ejecutar el servidor**

```bash
# Opción 1: Usando app.main (desarrollo)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Opción 2: Usando main.py (como en producción)
uvicorn main:app --host 0.0.0.0 --port 8000
```

6. **Acceder a la documentación**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🌐 Despliegue en Render (Free Tier)

### 🚀 Opción 1: Despliegue Automático con render.yaml

El proyecto incluye un archivo `render.yaml` para despliegue automático.

**Pasos:**

1. **Obtén tu API Key de Groq (GRATIS)**
   - Ve a https://console.groq.com/keys
   - Crea una cuenta gratuita
   - Genera un nuevo API key
   - **Free tier**: 30 requests/minuto, 14,400 requests/día

2. **Sube el código a GitHub**
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

3. **Verifica que todo esté listo**
   ```bash
   python verify_deployment.py
   ```
   
   Este script verifica:
   - ✅ Todos los archivos necesarios existen
   - ✅ requirements.txt tiene las dependencias correctas
   - ✅ Artefactos no son muy pesados (<100MB)
   - ✅ .env.example está configurado

4. **Crea el servicio en Render**
   - Ve a https://dashboard.render.com
   - Haz clic en **"New +"** → **"Blueprint"**
   - Conecta tu repositorio de GitHub
   - Render detectará automáticamente el `render.yaml`
   - **Antes de deployar**, configura las variables de entorno:

5. **Configurar Variables de Entorno** (⚠️ IMPORTANTE)

En el Blueprint screen, agrega:

| Variable | Valor | ¿Secreto? | Descripción |
|----------|-------|-----------|-------------|
| `GROQ_API_KEY` | `tu_api_key_de_groq` | ✅ Sí | API Key de Groq LLM |
| `CORS_ORIGINS` | `https://tu-frontend.vercel.app,http://localhost:3000` | No | Dominios permitidos |
| `BASE_URL` | `https://www.datos.gov.co/resource/jbjy-vk9h.json` | No | API datos.gov.co |
| `ENABLE_EMBEDDINGS` | `false` | No | Habilitar embeddings (ver nota) |

**📝 Nota sobre ENABLE_EMBEDDINGS:**
- `false` (recomendado para free tier): Solo usa ML + LLM (~200-300MB RAM)
- `true`: Habilita análisis semántico completo (~600-800MB RAM)
- Para Render free tier (512MB), **debe estar en `false`**

6. **Deploy**
   - Haz clic en **"Apply"**
   - Render creará y desplegará tu servicio automáticamente
   - El despliegue toma ~5-10 minutos

### 🔧 Opción 2: Despliegue Manual

1. **Crear nuevo Web Service**
   - Conecta tu repositorio de GitHub
   - Selecciona el repositorio

2. **Configuración del servicio**
   - **Name**: `radarcol-api` (o el nombre que prefieras)
   - **Environment**: `Python 3`
   - **Region**: `Oregon` (más cercano a Colombia)
   - **Branch**: `main`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

3. **Variables de Entorno** (⚠️ MUY IMPORTANTE)

En el Dashboard de Render, ve a **Environment** y agrega estas variables:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `GROQ_API_KEY` | `tu_api_key_aqui` | API Key de Groq (obtener en console.groq.com) |
| `CORS_ORIGINS` | `https://www.radarcol.com,https://radarcol.com` | Dominios permitidos para CORS (sin espacios) |
| `BASE_URL` | `https://www.datos.gov.co/resource/jbjy-vk9h.json` | URL de la API de datos.gov.co |
| `RUTA_ARTEFACTOS` | `data/artifacts` | Ruta a los artefactos del modelo ML |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `ENABLE_EMBEDDINGS` | `false` | ⚠️ Deshabilitar embeddings para free tier (512MB) |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo ligero (solo si ENABLE_EMBEDDINGS=true) |

**⚠️ IMPORTANTE - Configuración de Memoria:**

Render free tier tiene un límite de **512MB de RAM**. El motor de análisis tiene dos modos:

1. **Modo Ligero (Recomendado para Free Tier):**
   - `ENABLE_EMBEDDINGS=false`
   - Usa solo ML (IsolationForest) + LLM (Groq)
   - Consumo: ~200-300MB RAM
   - ✅ Funciona perfectamente en free tier

2. **Modo Completo (Requiere >1GB RAM):**
   - `ENABLE_EMBEDDINGS=true`
   - Usa ML + LLM + Embeddings semánticos
   - Consumo: ~600-800MB RAM
   - ❌ Excede límite de free tier → Error "Out of Memory"

Para planes pagos de Render con más memoria, puedes habilitar `ENABLE_EMBEDDINGS=true` para análisis semántico completo.

### ✅ Verificar el Despliegue

Una vez desplegado:

```bash
# Health check
curl https://tu-app.onrender.com/health

# Probar endpoint de contratos
curl https://tu-app.onrender.com/contratos?limit=5
```

### 💡 Consideraciones para Free Tier de Render

**Recursos disponibles:**
- ✅ 512MB RAM (suficiente para la API + modelos ML)
- ✅ CPU compartida (sin GPU, no necesaria con Groq API)
- ✅ 750 horas/mes de actividad
- ⚠️ El servicio se duerme después de 15 min de inactividad
- ⚠️ Primer request después de dormirse toma ~30 segundos

**Optimizaciones aplicadas:**
- Motor ML cargado en memoria (singleton pattern)
- Modelos pequeños y eficientes
- LLM inference via Groq API (no local)
- Artefactos comprimidos (<100MB)

### 🧠 ¿Por qué Groq en lugar de LLM local?

El proyecto usa **Groq API** en lugar de correr un LLM localmente porque:

1. **Render Free Tier no tiene GPU** - Imposible correr LLMs locales eficientemente
2. **512MB RAM limitados** - Incluso modelos pequeños (3-7B) necesitan 2-3GB mínimo
3. **Groq es gratuito** - 14,400 requests/día sin costo
4. **Ultra-baja latencia** - ~500 tokens/seg, más rápido que GPT-4
5. **Modelos potentes** - LLaMA 3.1 8B es superior a modelos locales pequeños

### 🔧 Configuración CORS en Producción

**⚠️ CRÍTICO**: Para que CORS funcione correctamente en producción:

1. En Render Dashboard, ve a **Environment**
2. Agrega la variable `CORS_ORIGINS` con **EXACTAMENTE** tus dominios:
   ```
   https://www.radarcol.com,https://radarcol.com
   ```
   - ✅ SIN espacios después de las comas
   - ✅ HTTPS para dominios en producción
   - ✅ Incluir tanto `www` como sin `www` si usas ambos

3. **Verifica los logs** después del despliegue:
   ```
   🔧 CORS Origins cargados desde variable de entorno:
      ✅ https://www.radarcol.com
      ✅ https://radarcol.com
   ```

### 📝 Logs de Debugging

La API incluye logging detallado que te ayudará a debuggear problemas de CORS:

**Al iniciar:**
```
🚀 API de Análisis de Contratos Gubernamentales iniciada
🌐 Ambiente: PRODUCCION
📊 BASE_URL: https://www.datos.gov.co/resource/jbjy-vk9h.json
🔧 CORS Origins cargados desde variable de entorno:
   ✅ https://www.radarcol.com
   ✅ https://radarcol.com
```

**En cada petición:**
```
📥 Petición entrante:
   • Método: GET
   • Path: /contratos
   • Origin: https://www.radarcol.com
   • Host: radarcol-api.onrender.com
   • User-Agent: Mozilla/5.0...
📤 Respuesta enviada:
   • Status: 200
   • Access-Control-Allow-Origin: https://www.radarcol.com
```

### 🔍 Troubleshooting CORS

Si experimentas errores de CORS en producción:

1. **Verifica los logs en Render**:
   - Ve a **Logs** en el Dashboard
   - Busca la sección de inicio con los emojis 🔧 o ⚠️
   - Confirma que los dominios listados son correctos

2. **Verifica los headers en el navegador**:
   - Abre DevTools (F12)
   - Ve a la pestaña **Network**
   - Selecciona la petición fallida
   - Verifica el header `Origin` que envía el navegador
   - Compara con los valores en `CORS_ORIGINS`

3. **Problemas comunes**:
   - ❌ Espacios en `CORS_ORIGINS`: `https://domain.com, https://other.com`
   - ✅ Sin espacios: `https://domain.com,https://other.com`
   - ❌ HTTP en producción: `http://www.radarcol.com`
   - ✅ HTTPS en producción: `https://www.radarcol.com`
   - ❌ Falta www o sin www: Solo incluir uno
   - ✅ Ambos incluidos: `https://www.radarcol.com,https://radarcol.com`

## � Solución de Problemas

### Error: "Could not import module 'main'"

Si Render muestra este error, verifica:

1. **Archivo main.py en la raíz**: El proyecto incluye un `main.py` en la raíz que importa desde `app.main`
   ```python
   from app.main import app
   __all__ = ["app"]
   ```

2. **Comando de inicio correcto**: Debe ser `uvicorn main:app` (no `uvicorn app.main:app`)

3. **Archivos de configuración presentes**:
   - `render.yaml`: Define el comando de inicio automáticamente
   - `Procfile`: Alternativa para el comando de inicio
   - `main.py`: Entry point en la raíz del proyecto

### Error: "Module 'numpy' has no attribute..."

Incompatibilidad de versiones. Solución:

```bash
pip install --upgrade numpy pandas scikit-learn
```

### Servicio se duerme (Free Tier)

El servicio Render Free se duerme tras 15 minutos de inactividad:

- ✅ **Normal**: El primer request tarda ~30 segundos
- 💡 **Solución**: Implementar un cron job que haga ping cada 10 minutos
- 🔄 **O**: Actualizar a plan pagado ($7/mes) para mantenerlo activo 24/7

### CORS Errors en Producción

Verifica en Render Dashboard → Environment:

```bash
CORS_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
```

- ✅ Sin espacios después de comas
- ✅ HTTPS en producción
- ✅ Incluir tanto www como sin www

## �📚 API Endpoints

### GET `/`

Health check del servicio.

**Response:**
```json
{
  "mensaje": "API de análisis de contratos funcionando correctamente",
  "version": "1.0.0"
}
```

### GET `/contratos`

Obtiene listado de contratos con filtros opcionales.

**Query Parameters:**

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `limit` | int | Límite de resultados (1-100) | `10` |
| `fecha_desde` | string | Fecha inicio (YYYY-MM-DD) | `2024-01-01` |
| `fecha_hasta` | string | Fecha fin (YYYY-MM-DD) | `2024-12-31` |
| `valor_minimo` | float | Valor mínimo del contrato | `1000000` |
| `valor_maximo` | float | Valor máximo del contrato | `10000000` |
| `nombre_contrato` | string | Nombre de la entidad | `ministerio` |
| `id_contrato` | string | ID específico del contrato | `ABC-123` |

**Ejemplo de petición:**
```bash
curl "http://localhost:8000/contratos?limit=10&fecha_desde=2024-01-01"
```

**Response:**
```json
{
  "metadata": {
    "total_contratos": 150,
    "total_valor_contratos": 50000000000,
    "contratos_alto_riesgo": 15.5
  },
  "contratos": [
    {
      "id": "ABC-123",
      "nombre_entidad": "Ministerio de Educación",
      "descripcion_contrato": "Construcción de infraestructura educativa",
      "fecha_inicio": "2024-03-15",
      "fecha_fin": "2024-12-31",
      "valor": 5000000000,
      "nivelRiesgo": "Bajo",
      "anomalia": false
    }
  ]
}
```

## 🧪 Testing

Prueba la API localmente:

```bash
# Health check
curl http://localhost:8000/

# Obtener contratos
curl http://localhost:8000/contratos?limit=5

# Con filtros
curl "http://localhost:8000/contratos?limit=10&fecha_desde=2024-01-01&valor_minimo=1000000"
```

## 📄 Licencia

Este proyecto utiliza datos abiertos de [datos.gov.co](https://www.datos.gov.co/).

## 👥 Contacto

Para consultas o soporte, contacta al equipo de desarrollo.

---

**Desarrollado con ❤️ usando FastAPI**
