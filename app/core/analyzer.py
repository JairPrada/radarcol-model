import joblib
import json
import numpy as np
import pandas as pd
import re
import time
import os
from groq import Groq
from sentence_transformers import SentenceTransformer

class RadarColInferencia:
    def __init__(self, groq_api_key=None, ruta_artefactos="data/artifacts"):
        print("⚙️ Inicializando Motor RadarCol (Groq + ML)...")
        
        # 1. Configuración Groq LLM
        self.usar_llm = False
        self.client = None
        self.model_name = "llama-3.1-8b-instant"  # Modelo rápido y eficiente
        
        try:
            # Si pasas la key explícita o está en variables de entorno
            if groq_api_key:
                self.client = Groq(api_key=groq_api_key)
            else:
                self.client = Groq()  # Busca GROQ_API_KEY en env
            
            self.usar_llm = True
            print(f"   ✨ Cliente Groq conectado ({self.model_name})")
            print(f"   📝 Free tier: 30 req/min, 14.4k req/día")
        except Exception as e:
            print(f"   ⚠️ Error cliente Groq: {e}. Se usará modo solo ML.")

        # 2. Cargar Artefactos Matemáticos (Con manejo de errores robusto)
        self.modo_solo_llm = False  # Flag para modo degradado
        try:
            print(f"   📁 Intentando cargar desde: {ruta_artefactos}")
            
            # Verificar que la ruta existe
            import os
            if not os.path.exists(ruta_artefactos):
                raise FileNotFoundError(f"Directorio de artefactos no encontrado: {ruta_artefactos}")
            
            self.iso_forest = joblib.load(f"{ruta_artefactos}/modelo_isoforest.pkl")
            self.centroide = np.load(f"{ruta_artefactos}/centroide_semantico.npy")
            with open(f"{ruta_artefactos}/stats_entidades.json", 'r') as f:
                self.stats_entidades = json.load(f)
            
            # SHAP
            try:
                self.shap_explainer = joblib.load(f"{ruta_artefactos}/shap_explainer.pkl")
                self.usar_shap = True
                print("   ✅ SHAP explainer cargado correctamente")
            except:
                self.usar_shap = False
                print("   ⚠️ SHAP no disponible (continuando sin explicabilidad).")
                
            print("   ✅ Artefactos cargados correctamente")
        except Exception as e:
            print(f"   ⚠️ ADVERTENCIA: Fallo cargando artefactos en {ruta_artefactos}: {e}")
            print("   🔄 Activando modo degradado (solo LLM + valores por defecto)")
            
            # Modo degradado: usar valores por defecto
            self.modo_solo_llm = True
            self.iso_forest = None
            self.stats_entidades = {
                # Estadísticas por defecto para entidades comunes
                "default": {"media": 50000000, "std": 20000000}
            }
            self.usar_shap = False

        # 3. NLP - Carga condicional basada en configuración
        self.model_nlp = None
        
        # Importar configuración de embeddings
        try:
            from app.config import ENABLE_EMBEDDINGS, EMBEDDING_MODEL
            self.enable_embeddings = ENABLE_EMBEDDINGS
            self.embedding_model_name = EMBEDDING_MODEL
        except ImportError:
            # Valores por defecto si no hay configuración
            self.enable_embeddings = False
            self.embedding_model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        
        if self.enable_embeddings:
            try:
                print(f"   🧠 Cargando embeddings: {self.embedding_model_name}")
                print("   ⏱️  Esto puede tomar 10-30 segundos...")
                self.model_nlp = SentenceTransformer(
                    self.embedding_model_name, 
                    device="cpu"
                )
                print(f"   ✅ Embeddings cargados correctamente")
            except Exception as e:
                print(f"   ⚠️ Error cargando embeddings: {e}")
                print("   🔄 Continuando sin análisis semántico (solo ML + LLM)")
                self.model_nlp = None
                self.enable_embeddings = False
        else:
            print("   ⚙️  Embeddings deshabilitados (modo bajo consumo de memoria)")
            print("   ℹ️  El análisis usará solo ML + LLM (sin score semántico)")
        
        self.columnas_modelo = [
            "Z-Score Valor", "Valor Logaritmo", "Costo por Caracter", 
            "Indice Dependencia Proveedor", "Pct Tiempo Adicionado",
            "Duracion Dias", "Dias tras Firma", "Anio Firma", "Mes Firma"
        ]

    def _preprocesar(self, contrato):
        valor = float(contrato.get("Valor del Contrato", 0))
        objeto = contrato.get("Objeto del Contrato", "Sin descripción")
        nit = contrato.get("Nit Entidad", "0")
        duracion = float(contrato.get("Duracion Dias", 0))
        
        # Obtener estadísticas de entidad
        if self.modo_solo_llm or not self.stats_entidades:
            # Modo degradado: usar estadísticas por defecto
            fallback_stats = {"media": 50000000, "std": 20000000}
            stats = fallback_stats
        else:
            fallback_stats = {"media": 50000000, "std": 20000000}
            stats = self.stats_entidades.get(nit, 
                    self.stats_entidades.get("default", fallback_stats))
        
        std = stats['std'] if stats['std'] > 0 else 1.0
        z_score = (valor - stats['media']) / std
        
        features = {
            "Z-Score Valor": z_score,
            "Valor Logaritmo": np.log(valor + 1),
            "Costo por Caracter": valor / (len(objeto) + 1),
            "Indice Dependencia Proveedor": float(contrato.get("Indice Dependencia", 0)),
            "Pct Tiempo Adicionado": 0.0,
            "Duracion Dias": duracion,
            "Dias tras Firma": 0,
            "Anio Firma": contrato.get("Anio Firma", 2025),
            "Mes Firma": contrato.get("Mes Firma", 1)
        }
        return pd.DataFrame([features])[self.columnas_modelo], objeto, features

    def _limpiar_json_llm(self, texto):
        """Usa Regex para extraer JSON válido de cualquier respuesta."""
        try:
            match = re.search(r'\{.*\}', texto, re.DOTALL)
            if match: return json.loads(match.group())
            return json.loads(texto)
        except: return None

    def _generar_con_retry(self, prompt):
        """Llama a Groq API con reintentos automáticos."""
        for i in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Respuestas consistentes
                    max_tokens=1000   # Límite para análisis
                )
                return response.choices[0].message.content
            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower():
                    wait_time = 12 + (i * 8)  # Espera progresiva para rate limits
                    print(f"   ⏳ Rate limit, esperando {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Error Groq API: {err}")
                    break
        return None

    def _generar_analisis_ia(self, contrato, riesgo, nivel, features, shap_values, score_ml, score_nlp):
        
        # --- LÓGICA DE PERSONALIDAD ADAPTATIVA ---
        
        # CASO 1: Contrato Normal (BAJO RIESGO)
        if nivel == "BAJO":
            rol = "Eres un Auditor de Calidad validando un proceso correcto."
            instruccion = f"""
            El análisis matemático confirma que este contrato es NORMAL (Riesgo Bajo: {riesgo:.0%}).
            
            TAREA:
            Escribe un reporte corto confirmando la regularidad del contrato.
            - Resumen: Indica que el monto (${contrato.get('Valor del Contrato',0):,.0f}) y el objeto son consistentes con el histórico de la entidad.
            - Factores: Menciona "Monto dentro del promedio" y "Descripción clara".
            - Recomendaciones: Sugiere "Archivar expediente" o "Continuar trámite".
            
            TONO: Tranquilizador, profesional, de visto bueno.
            """
            
        # CASO 2: Contrato Sospechoso (MEDIO / ALTO / CRÍTICO)
        else:
            rol = "Eres un Auditor Forense experto en detección de fraude."
            
            # Preparamos evidencia para el prompt
            txt_shap = ""
            if shap_values:
                top_3 = shap_values[:3]
                txt_shap = "Variables clave:\n" + "\n".join([f"- {i['variable']} (Valor: {i['valor']})" for i in top_3])

            instruccion = f"""
            ALERTA: El sistema detectó RIESGO {nivel} ({riesgo:.0%}).
            
            EVIDENCIA:
            1. Score Financiero (ML): {score_ml:.0%}
            2. Score Semántico (Texto): {score_nlp:.0%}
            3. Desviación Precio (Z-Score): {features['Z-Score Valor']:.1f}x veces el promedio.
            {txt_shap}
            
            TAREA:
            Explica las anomalías detectadas.
            - Resumen: Enfócate en por qué el monto no cuadra con el objeto.
            - Factores: Lista qué variables matemáticas dispararon la alerta.
            - Recomendaciones: Sugiere auditorías específicas (fiscal, precios, jurídica).
            
            TONO: Alerta, crítico, preventivo.
            """

        prompt = f"""
        {rol}
        
        DATOS:
        - Objeto: "{contrato.get('Objeto del Contrato')}"
        - Valor: ${contrato.get('Valor del Contrato', 0):,.0f}
        
        {instruccion}

        SALIDA JSON OBLIGATORIA:
        {{
            "resumen": "Texto...",
            "factores": ["Texto...", "Texto..."],
            "recomendaciones": ["Texto...", "Texto..."]
        }}
        """
        
        raw = self._generar_con_retry(prompt)
        if raw:
            data = self._limpiar_json_llm(raw)
            if data: 
                # Asegurar que sean listas de strings simples
                data["factores"] = [str(x) for x in data.get("factores", [])]
                data["recomendaciones"] = [str(x) for x in data.get("recomendaciones", [])]
                return data

        # Fallback de emergencia
        return {
            "resumen": "Análisis completado. Revise los indicadores numéricos.",
            "factores": ["Análisis matemático completado"],
            "recomendaciones": ["Validación manual"]
        }

    def analizar_contrato_ml_solo(self, contrato_json):
        """Análisis rápido solo con ML, sin LLM (para endpoint /contratos)."""
        X, texto, features = self._preprocesar(contrato_json)
        
        # 1. Score ML (Financiero)
        if self.iso_forest and not self.modo_solo_llm:
            try:
                score_raw = self.iso_forest.decision_function(X)[0]
                risk_ml = float(np.clip(1 - ((score_raw - (-0.5)) / (0.5 - (-0.5))), 0, 1))
            except Exception as e:
                print(f"   ⚠️ Error en Isolation Forest: {e}. Usando z-score como fallback.")
                # Calcular riesgo basado en z-score como fallback
                z_score = features.get("Z-Score Valor", 0)
                risk_ml = float(min(abs(z_score) / 5.0, 1.0))
                score_raw = -risk_ml  # Simular score para compatibilidad
        else:
            # Modo degradado: usar z-score como proxy de riesgo
            z_score = features.get("Z-Score Valor", 0)
            risk_ml = float(min(abs(z_score) / 5.0, 1.0))
            score_raw = -risk_ml
        
        # VETO: Si el precio es absurdo (Z > 3), Riesgo es 1.0 siempre
        if features["Z-Score Valor"] > 3: 
            risk_ml = 1.0
        
        # 2. Score NLP (Semántico)
        # Si embeddings están deshabilitados, usar score neutral (0.0)
        risk_nlp = 0.0
        
        if self.model_nlp and hasattr(self, 'centroide'):
            try:
                emb = self.model_nlp.encode(
                    texto[:200], 
                    convert_to_numpy=True, 
                    show_progress_bar=False, 
                    normalize_embeddings=True
                )
                dist = np.linalg.norm(emb - self.centroide)
                risk_nlp = float(np.clip(dist / 2.0, 0, 1))
            except Exception as e:
                print(f"   ⚠️ Error calculando embeddings: {e}")
                risk_nlp = 0.0
        
        # Si no hay embeddings, el análisis se basa solo en ML
        
        # 3. SHAP (explicabilidad)
        shap_values = []
        if self.usar_shap:
            try:
                sv = self.shap_explainer.shap_values(X)
                if isinstance(sv, list): sv = sv[0]
                shap_values = [{"variable": col, "valor": float(val)} 
                              for col, val in zip(self.columnas_modelo, sv[0])]
            except: pass
        
        # 4. Combinación final
        # Si embeddings están habilitados: 70% ML, 30% NLP
        # Si embeddings deshabilitados: 100% ML (risk_nlp es 0.0)
        if self.model_nlp:
            score_combinado = risk_ml * 0.7 + risk_nlp * 0.3
        else:
            # Sin embeddings, confiar 100% en el análisis ML/financiero
            score_combinado = risk_ml
        
        # 5. Determinar nivel de riesgo
        if score_combinado >= 0.7:
            nivel = "CRÍTICO"
        elif score_combinado >= 0.5:
            nivel = "ALTO" 
        elif score_combinado >= 0.3:
            nivel = "MEDIO"
        else:
            nivel = "BAJO"
        
        return {
            "Meta_Data": {
                "Score": float(score_combinado),
                "Riesgo": nivel,
                "Score_IsolationForest": float(risk_ml),
                "Score_NLP_Embeddings": float(risk_nlp),
                "Raw_IsolationForest": float(score_raw) if self.iso_forest else None,
                "Distancia_Semantica": float(risk_nlp * 2.0)
            },
            "Detalle_SHAP": shap_values,
            "Analisis_LLM": None  # Sin análisis LLM para rapidez
        }

    def analizar_contrato(self, contrato_json, incluir_llm=True):
        """Análisis completo con ML + LLM opcional (para análisis detallado)."""
        # Primero obtener análisis ML
        resultado_ml = self.analizar_contrato_ml_solo(contrato_json)
        
        # Si no se requiere LLM o no está disponible, retornar solo ML
        if not incluir_llm or not self.usar_llm:
            return resultado_ml
        
        # Análisis LLM adicional para análisis detallado
        X, texto, features = self._preprocesar(contrato_json)
        
        score_combinado = resultado_ml["Meta_Data"]["Score"]
        nivel = resultado_ml["Meta_Data"]["Riesgo"]
        shap_values = resultado_ml["Detalle_SHAP"]
        risk_ml = resultado_ml["Meta_Data"]["Score_IsolationForest"]
        risk_nlp = resultado_ml["Meta_Data"]["Score_NLP_Embeddings"]
        
        # Generar análisis LLM detallado
        analisis_llm = self._generar_analisis_ia(
            contrato_json, score_combinado, nivel, features, shap_values, risk_ml, risk_nlp
        )
        
        # Combinar resultados ML + LLM
        resultado_completo = resultado_ml.copy()
        resultado_completo["Analisis_LLM"] = analisis_llm
        
        return resultado_completo