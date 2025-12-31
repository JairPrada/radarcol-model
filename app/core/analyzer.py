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

        # 2. Cargar Artefactos Matemáticos (Con manejo de errores)
        try:
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
            print(f"   ❌ ERROR CRÍTICO: Fallo cargando artefactos en {ruta_artefactos}: {e}")
            self.iso_forest = None
            self.stats_entidades = {}
            self.usar_shap = False

        # 3. NLP
        try:
            print("   🧠 Cargando embeddings (esto toma unos segundos)...")
            self.model_nlp = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es', device="cpu")
        except:
            print("   ⚠️ Error NLP. La semántica será ignorada.")
            self.model_nlp = None
        
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
        
        fallback_stats = {"media": 50000000, "std": 20000000}
        stats = self.stats_entidades.get(nit, fallback_stats)
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
        score_raw = self.iso_forest.decision_function(X)[0] if self.iso_forest else 0
        risk_ml = float(np.clip(1 - ((score_raw - (-0.5)) / (0.5 - (-0.5))), 0, 1))
        
        # VETO: Si el precio es absurdo (Z > 3), Riesgo es 1.0 siempre
        if features["Z-Score Valor"] > 3: 
            risk_ml = 1.0
        
        # 2. Score NLP (Semántico)
        risk_nlp = 0.5
        if self.model_nlp:
            emb = self.model_nlp.encode(texto[:200], convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
            c = self.centroide if hasattr(self, 'centroide') else np.zeros(emb.shape)
            dist = np.linalg.norm(emb - c) if c.size > 0 else 1.0
            risk_nlp = float(np.clip(dist / 2.0, 0, 1))
        
        # 3. SHAP (explicabilidad)
        shap_values = []
        if self.usar_shap:
            try:
                sv = self.shap_explainer.shap_values(X)
                if isinstance(sv, list): sv = sv[0]
                shap_values = [{"variable": col, "valor": float(val)} 
                              for col, val in zip(self.columnas_modelo, sv[0])]
            except: pass
        
        # 4. Combinación final (70% ML, 30% NLP)
        score_combinado = risk_ml * 0.7 + risk_nlp * 0.3
        
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