# Script de verificación pre-deployment
Write-Host "=== Verificación del Build ===" -ForegroundColor Cyan

# 1. Verificar estructura de carpetas
Write-Host "`n1. Verificando estructura de carpetas..." -ForegroundColor Yellow
$folders = @("app/core", "app/controllers", "app/services", "app/models", "app/config", "data/artifacts")
foreach ($folder in $folders) {
    if (Test-Path $folder) {
        Write-Host "   ✓ $folder" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $folder NO EXISTE" -ForegroundColor Red
        exit 1
    }
}

# 2. Verificar artefactos ML
Write-Host "`n2. Verificando artefactos ML..." -ForegroundColor Yellow
$artifacts = @(
    "data/artifacts/modelo_isoforest.pkl",
    "data/artifacts/centroide_semantico.npy",
    "data/artifacts/stats_entidades.json",
    "data/artifacts/shap_explainer.pkl"
)
foreach ($artifact in $artifacts) {
    if (Test-Path $artifact) {
        $size = (Get-Item $artifact).Length / 1KB
        Write-Host "   ✓ $artifact ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $artifact NO EXISTE" -ForegroundColor Red
        exit 1
    }
}

# 3. Verificar archivos de configuración
Write-Host "`n3. Verificando archivos de configuración..." -ForegroundColor Yellow
$configs = @("requirements.txt", ".env.example", "README.md")
foreach ($config in $configs) {
    if (Test-Path $config) {
        Write-Host "   ✓ $config" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ $config" -ForegroundColor Yellow
    }
}

# 4. Verificar imports Python
Write-Host "`n4. Verificando imports Python..." -ForegroundColor Yellow
try {
    python -c "import app.core.analyzer; print('   ✓ app.core.analyzer')"
    python -c "import app.services.contract_service; print('   ✓ app.services.contract_service')"
    python -c "from app.main import app; print('   ✓ app.main')" 2>$null
    Write-Host "   ✓ Todos los imports OK" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Error en imports" -ForegroundColor Red
    exit 1
}

# 5. Verificar dependencias
Write-Host "`n5. Verificando dependencias críticas..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "groq", "scikit-learn", "sentence-transformers", "shap")
foreach ($pkg in $packages) {
    $installed = pip show $pkg 2>$null
    if ($installed) {
        $version = ($installed | Select-String "Version:").ToString().Split(":")[1].Trim()
        Write-Host "   ✓ $pkg ($version)" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $pkg NO INSTALADO" -ForegroundColor Red
    }
}

# 6. Verificar variables de entorno
Write-Host "`n6. Verificando variables de entorno..." -ForegroundColor Yellow
if (Test-Path .env) {
    $envContent = Get-Content .env
    if ($envContent -match "GROQ_API_KEY") {
        Write-Host "   ✓ GROQ_API_KEY configurada" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ GROQ_API_KEY no encontrada en .env" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠ Archivo .env no existe (usar .env.example)" -ForegroundColor Yellow
}

Write-Host "`n=== Build verificado exitosamente ===" -ForegroundColor Green
Write-Host "`nPara iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  uvicorn app.main:app --reload --port 8000" -ForegroundColor White
