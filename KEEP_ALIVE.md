# ⚡ Configuración de Keep-Alive para Render

## 🚨 Problema: Cold Start en Render

Render en el plan gratuito pone tu servicio en "sleep mode" después de **15 minutos de inactividad**. La primera petición después del sleep tarda **30-60 segundos** en responder.

## ✅ Solución: Health Check Automático

Usa un servicio externo gratuito para hacer "ping" a tu API cada 5 minutos y mantenerla activa.

---

## 🔧 Opción 1: UptimeRobot (Recomendado)

**Ventajas:** Gratuito, fácil de usar, incluye alertas por email

### Pasos:

1. **Crear cuenta** en https://uptimerobot.com (gratuita)

2. **Agregar nuevo monitor:**
   - Click en "Add New Monitor"
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: RadarCol API Keep-Alive
   - **URL**: `https://radarcol-model-api.onrender.com/health`
   - **Monitoring Interval**: 5 minutes (gratis)
   - Click "Create Monitor"

3. **Listo!** Tu API se mantendrá activa 24/7

---

## 🔧 Opción 2: Cron-Job.org

**Ventajas:** Muy configurable, múltiples checks por hora

### Pasos:

1. **Crear cuenta** en https://cron-job.org (gratuita)

2. **Crear cron job:**
   - Click en "Create Cronjob"
   - **Title**: RadarCol API Keep-Alive
   - **URL**: `https://radarcol-model-api.onrender.com/health`
   - **Schedule**: `*/5 * * * *` (cada 5 minutos)
   - **Enable**: ON
   - Click "Create"

3. **Listo!** El cron job mantendrá tu API activa

---

## 🔧 Opción 3: GitHub Actions (Avanzado)

Si quieres mantener todo en tu repositorio:

### Crear archivo: `.github/workflows/keep-alive.yml`

```yaml
name: Keep API Alive

on:
  schedule:
    # Cada 5 minutos
    - cron: '*/5 * * * *'
  workflow_dispatch: # Permite ejecución manual

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping API Health Endpoint
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://radarcol-model-api.onrender.com/health)
          echo "API responded with status: $response"
          if [ $response -ne 200 ]; then
            echo "❌ API health check failed!"
            exit 1
          fi
          echo "✅ API is healthy"
```

**Nota:** GitHub Actions tiene límites de ejecución mensual en cuentas gratuitas.

---

## 📊 Verificar que Funciona

1. **Accede al endpoint health:**
   ```bash
   curl https://radarcol-model-api.onrender.com/health
   ```

2. **Respuesta esperada:**
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-12-23T15:30:00Z",
     "service": "radarcol-api",
     "version": "1.0.0"
   }
   ```

3. **Monitorea en los logs de Render:**
   - Ve al Dashboard de Render
   - Abre tu servicio
   - Click en "Logs"
   - Deberías ver peticiones GET /health cada 5 minutos

---

## ⚠️ Consideraciones

### ✅ Ventajas:
- Elimina completamente el cold start
- Usuarios siempre tendrán respuestas rápidas
- Solución 100% gratuita

### ⚠️ Desventajas:
- Consume horas de build/run de Render (750 hrs/mes gratis)
- Si tienes mucho tráfico, considera upgrade a plan pagado

### 💡 Cálculo de consumo:
- 1 mes = ~720 horas
- Con keep-alive activo 24/7 = 720 horas
- Render plan gratuito = 750 horas/mes
- **Margen**: 30 horas (suficiente)

---

## 🚀 Plan Pagado de Render (Opcional)

Si tu aplicación es crítica, considera el plan **Starter** de Render:

- **$7/mes** (facturación mensual)
- Sin cold starts (siempre activo)
- Mejor rendimiento
- Más horas de cómputo

**Enlace**: https://render.com/pricing

---

## 🧪 Testing Local

Puedes probar el endpoint localmente:

```bash
# Iniciar API
uvicorn main:app --reload

# En otra terminal
curl http://localhost:8000/health
```

---

## 📝 Logs y Monitoreo

El endpoint `/health` aparecerá en tus logs de Render:

```
2025-12-23 15:30:00 - main - INFO - 📥 Petición entrante:
2025-12-23 15:30:00 - main - INFO -    • Método: GET
2025-12-23 15:30:00 - main - INFO -    • Path: /health
2025-12-23 15:30:00 - main - INFO -    • User-Agent: UptimeRobot/2.0
```

Estos logs te confirman que el keep-alive está funcionando.

---

**¿Preguntas?** Revisa la documentación de tu servicio de monitoring elegido.
