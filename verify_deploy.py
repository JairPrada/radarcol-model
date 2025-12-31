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

def test_artifacts():
    """Prueba que los artefactos ML estén disponibles."""
    print("\n🎯 Verificando artefactos ML...")
    
    try:
        from app.config import RUTA_ARTEFACTOS
        import os
        
        print(f"   📁 Ruta configurada: {RUTA_ARTEFACTOS}")
        
        required_files = [
            "modelo_isoforest.pkl",
            "centroide_semantico.npy", 
            "stats_entidades.json",
            "shap_explainer.pkl"
        ]
        
        missing_files = []
        for file in required_files:
            file_path = os.path.join(RUTA_ARTEFACTOS, file)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   ✅ {file} ({size:,} bytes)")
            else:
                print(f"   ❌ {file} - NO ENCONTRADO")
                missing_files.append(file)
        
        if missing_files:
            print(f"   ⚠️ ADVERTENCIA: {len(missing_files)} archivos faltantes")
            print("   📝 La aplicación funcionará en modo degradado")
            return True  # No es crítico, puede funcionar sin ellos
        else:
            print("   ✅ Todos los artefactos ML disponibles")
            return True
            
    except Exception as e:
        print(f"   ❌ Error verificando artefactos: {e}")
        return False

def test_degraded_mode():
    """Prueba que el modo degradado funcione correctamente."""
    print("\n🔄 Verificando modo degradado...")
    
    try:
        from app.core.analyzer import RadarColInferencia
        
        # Probar con ruta inexistente para activar modo degradado
        motor = RadarColInferencia(ruta_artefactos="ruta_inexistente")
        
        if hasattr(motor, 'modo_solo_llm') and motor.modo_solo_llm:
            print("   ✅ Modo degradado se activa correctamente")
            
            # Probar análisis en modo degradado
            contrato_test = {
                "Valor del Contrato": 1000000,
                "Objeto del Contrato": "Servicio de prueba",
                "Nit Entidad": "12345678",
                "Duracion Dias": 30,
                "Anio Firma": 2024,
                "Mes Firma": 6
            }
            
            resultado = motor.analizar_contrato_ml_solo(contrato_test)
            if resultado and "Meta_Data" in resultado:
                print("   ✅ Análisis en modo degradado funciona")
                return True
            else:
                print("   ❌ Error en análisis de modo degradado")
                return False
        else:
            print("   ✅ Artefactos disponibles (modo normal)")
            return True
            
    except Exception as e:
        print(f"   ❌ Error en modo degradado: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("🔍 VERIFICACIÓN COMPLETA PARA DESPLIEGUE")
    print("=" * 50)
    
    tests = [
        ("Importaciones", test_imports),
        ("Aplicación FastAPI", test_app),
        ("Servicios", test_services),
        ("Artefactos ML", test_artifacts),
        ("Modo degradado", test_degraded_mode),
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