# 🚀 API de Análisis de Contratos Gubernamentales

API FastAPI para el análisis y consulta de contratos del sector público colombiano desde la plataforma SECOP II (datos.gov.co).

## 📋 Características

- ✅ **Consulta de contratos**: Información detallada de contratos gubernamentales
- 🔍 **Filtrado avanzado**: Por fecha, valor, entidad e ID
- 📊 **Análisis de riesgo**: Evaluación de niveles de riesgo y anomalías
- 📈 **Métricas agregadas**: Estadísticas y análisis de alto nivel
- 🔐 **CORS configurado**: Soporte para múltiples orígenes
- 📝 **Logging completo**: Debugging detallado para producción

## 🛠️ Tecnologías

- **FastAPI** 0.125.0 - Framework web moderno y rápido
- **Uvicorn** 0.38.0 - Servidor ASGI de alto rendimiento
- **Pydantic** 2.12.3 - Validación de datos con tipos
- **Python-dotenv** 1.0.0 - Gestión de variables de entorno
- **Requests** 2.32.3 - Cliente HTTP

## 📁 Estructura del Proyecto

```
backend/
├── app/                          # Paquete principal de la aplicación
│   ├── __init__.py
│   ├── main.py                   # Punto de entrada FastAPI
│   ├── config/                   # Configuraciones
│   │   ├── __init__.py
│   │   └── settings.py          # Variables de entorno y configuración
│   ├── constants/               # Constantes y documentación
│   │   ├── __init__.py
│   │   └── documentation.py     # Textos de documentación de la API
│   ├── models/                  # Modelos Pydantic
│   │   ├── __init__.py
│   │   └── schemas.py           # DTOs y modelos de datos
│   ├── middlewares/             # Middlewares personalizados
│   │   ├── __init__.py
│   │   └── logging.py           # Middleware de logging
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

# Motor de Análisis IA
GEMINI_API_KEY=tu_api_key_de_gemini_aqui
RUTA_ARTEFACTOS=artefactos
```

5. **Ejecutar el servidor**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Acceder a la documentación**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🌐 Despliegue en Render

### Configuración en Dashboard de Render

1. **Crear nuevo Web Service**
   - Conecta tu repositorio de GitHub
   - Selecciona el repositorio `radarcol-model`

2. **Configuración del servicio**
   - **Name**: `radarcol-api` (o el nombre que prefieras)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Variables de Entorno** (⚠️ MUY IMPORTANTE)

En el Dashboard de Render, ve a **Environment** y agrega estas variables:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `CORS_ORIGINS` | `https://www.radarcol.com,https://radarcol.com` | Dominios permitidos para CORS (separados por comas, sin espacios) |
| `BASE_URL` | `https://www.datos.gov.co/resource/jbjy-vk9h.json` | URL de la API de datos.gov.co |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `GEMINI_API_KEY` | `tu_api_key_aqui` | API Key de Google Gemini para IA generativa |
| `RUTA_ARTEFACTOS` | `artefactos` | Ruta a los artefactos del modelo ML |
| `PORT` | (automático en Render) | Puerto asignado por Render |

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

## 📚 API Endpoints

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
