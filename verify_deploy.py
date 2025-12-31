#!/usr/bin/env python3
"""
Script de verificación completa para despliegue.
Verifica que todas las dependencias y funcionalidades principales funcionen.
"""

def test_imports():
    """Prueba todas las importaciones críticas."""
    print("🧪 Verificando importaciones...")
    
    try:
        import fastapi
        print(f"   ✅ fastapi {fastapi.__version__}")
    except ImportError as e:
        print(f"   ❌ fastapi: {e}")
        return False
    
    try:
        import uvicorn
        print(f"   ✅ uvicorn {uvicorn.__version__}")
    except ImportError as e:
        print(f"   ❌ uvicorn: {e}")
        return False
    
    try:
        import libsql
        print(f"   ✅ libsql disponible")
    except ImportError as e:
        print(f"   ⚠️ libsql no disponible (caché deshabilitado): {e}")
    
    try:
        import numpy
        print(f"   ✅ numpy {numpy.__version__}")
    except ImportError as e:
        print(f"   ❌ numpy: {e}")
        return False
    
    try:
        import pandas
        print(f"   ✅ pandas {pandas.__version__}")
    except ImportError as e:
        print(f"   ❌ pandas: {e}")
        return False
    
    try:
        import sklearn
        print(f"   ✅ scikit-learn {sklearn.__version__}")
    except ImportError as e:
        print(f"   ❌ scikit-learn: {e}")
        return False
    
    try:
        import joblib
        print(f"   ✅ joblib {joblib.__version__}")
    except ImportError as e:
        print(f"   ❌ joblib: {e}")
        return False
    
    return True

def test_app():
    """Prueba que la aplicación se puede inicializar."""
    print("\n🚀 Verificando aplicación FastAPI...")
    
    try:
        from app.main import app
        print("   ✅ Aplicación FastAPI inicializada")
        
        # Verificar que tenga endpoints
        routes = [route.path for route in app.routes]
        print(f"   ✅ {len(routes)} rutas encontradas")
        
        # Verificar endpoints críticos
        if "/contratos" in str(routes):
            print("   ✅ Endpoint /contratos disponible")
        else:
            print("   ⚠️ Endpoint /contratos no encontrado")
            
        return True
    except Exception as e:
        print(f"   ❌ Error inicializando aplicación: {e}")
        return False

def test_services():
    """Prueba servicios críticos."""
    print("\n⚙️ Verificando servicios...")
    
    try:
        from app.services.contract_service import ContractService
        print("   ✅ ContractService disponible")
    except Exception as e:
        print(f"   ❌ ContractService: {e}")
        return False
    
    try:
        from app.services.cache_service import CacheService
        cache = CacheService()
        print(f"   ✅ CacheService disponible (habilitado: {cache.is_enabled})")
    except Exception as e:
        print(f"   ❌ CacheService: {e}")
        return False
    
    try:
        from app.core.analyzer import RadarColInferencia
        print("   ✅ Motor de análisis RadarCol disponible")
    except Exception as e:
        print(f"   ❌ Motor de análisis: {e}")
        return False
    
    return True

def test_models():
    """Prueba modelos Pydantic."""
    print("\n📋 Verificando modelos de datos...")
    
    try:
        from app.models import ShapValueModel, AnalysisModel, ContractDetailModel
        
        # Crear modelo de prueba
        shap = ShapValueModel(
            variable="test_var",
            value=1.23,
            description="Variable de prueba",
            actualValue="Valor de prueba"
        )
        print("   ✅ ShapValueModel funciona correctamente")
        
        return True
    except Exception as e:
        print(f"   ❌ Error con modelos: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("🔍 VERIFICACIÓN COMPLETA PARA DESPLIEGUE")
    print("=" * 50)
    
    tests = [
        ("Importaciones", test_imports),
        ("Aplicación FastAPI", test_app),
        ("Servicios", test_services),
        ("Modelos de datos", test_models),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"\n❌ Error en {test_name}: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ TODAS LAS PRUEBAS PASARON - LISTO PARA DESPLIEGUE")
        return 0
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON - REVISAR ANTES DE DESPLEGAR")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())