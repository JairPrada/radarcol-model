import joblib
import json
import numpy as np
import pandas as pd
from google import genai 
from sentence_transformers import SentenceTransformer
import time
import os

class RadarColInferencia:
    def __init__(self, api_key_gemini=None, ruta_artefactos="data/artefactos"):
        try:
            print(f"Inicializando Motor RadarCol (V2.5 + Datos Graficos)...")
        except:
            print("Inicializando Motor RadarCol...")
        
        # 1. Configurar Cliente Gemini
        self.usar_llm = False
        self.client = None
        self.model_name = "gemini-2.5-flash"
        
        try:
            if api_key_gemini:
                self.client = genai.Client(api_key=api_key_gemini)
            else:
                self.client = genai.Client()
            self.usar_llm = True
            print(f"   [OK] Cliente GenAI conectado ({self.model_name}).")
        except Exception as e:
            print(f"   [WARN] Error inicializando cliente GenAI: {e}")

        # 2. Cargar Artefactos
        try:
            self.iso_forest = joblib.load(f"{ruta_artefactos}/modelo_isoforest.pkl")
            self.centroide = np.load(f"{ruta_artefactos}/centroide_semantico.npy")
            with open(f"{ruta_artefactos}/stats_entidades.json", 'r') as f:
                self.stats_entidades = json.load(f)
            try:
                self.shap_explainer = joblib.load(f"{ruta_artefactos}/shap_explainer.pkl")
                self.usar_shap = True
            except:
                self.usar_shap = False
            print("   [OK] Cerebros matematicos cargados.")
        except:
            self.iso_forest = None
            self.stats_entidades = {}
            self.usar_shap = False
            self.model_nlp = None

        # 3. NLP
        try:
            self.model_nlp = SentenceTransformer('hiiamsid/sentence_similarity_spanish_es', device="cpu")
        except:
            pass
        
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
        z_score = (valor - stats['media']) / (stats['std'] + 1e-9)
        
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

    def _generar_con_retry(self, prompt):
        intentos = 3
        for i in range(intentos):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    time.sleep(12 + (i * 5))
                else:
                    break
        return None

    def _generar_analisis_ia(self, contrato, riesgo, nivel, features, var_shap):
        prompt = f"""
        Actúa como Auditor Forense. Analiza este contrato y devuelve SOLO JSON.
        
        CONTEXTO:
        - Objeto: "{contrato.get('Objeto del Contrato')}"
        - Valor: ${contrato.get('Valor del Contrato'):,.0f}
        - Entidad: {contrato.get('Nit Entidad')}
        
        EVIDENCIA:
        - Riesgo: {nivel} ({riesgo:.2f}/1.0)
        - Z-Score: {features['Z-Score Valor']:.1f}
        - Factor Clave: "{var_shap}"

        FORMATO JSON:
        {{
            "resumen": "Explicación técnica de la anomalía...",
            "factores": ["1. Monto...", "2. Entidad...", "3. Objeto...", "4. Factor Técnico..."],
            "recomendaciones": ["→ Acción 1", "→ Acción 2", "→ Acción 3"]
        }}
        """
        texto = self._generar_con_retry(prompt)
        if texto:
            try:
                return json.loads(texto.replace("```json", "").replace("```", "").strip())
            except: pass
        return {"resumen": "Error IA", "factores": [], "recomendaciones": []}

    def analizar_contrato(self, contrato_json):
        X, texto, features = self._preprocesar(contrato_json)
        
        # 1. ML Score
        risk_ml = 0.95
        if self.iso_forest:
            score_raw = self.iso_forest.decision_function(X)
            risk_ml = float(np.clip(1 - ((score_raw - (-0.5)) / (0.5 - (-0.5))), 0, 1)[0])
        
        if features["Z-Score Valor"] > 3: risk_ml = 1.0
        
        # 2. NLP Score
        risk_nlp = 0.5
        if hasattr(self, 'model_nlp') and self.model_nlp:
             emb = self.model_nlp.encode(texto[:200], convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
             c = self.centroide if hasattr(self, 'centroide') else np.zeros(emb.shape)
             risk_nlp = float(np.clip(float(np.linalg.norm(emb - c)) / 1.2, 0, 1))

        indice_final = (risk_ml * 0.5) + (risk_nlp * 0.5)
        nivel_alerta = "CRÍTICO" if indice_final > 0.8 else "ALTO" if indice_final > 0.5 else "BAJO"

        # 3. SHAP COMPLETO (Para Gráficas)
        datos_grafica = [] # Lista vacía por defecto
        var_shap = "Análisis General"
        
        if self.usar_shap and self.iso_forest:
            v = self.shap_explainer.shap_values(X)
            vals = v[0] if isinstance(v, list) else v
            if len(vals.shape) > 1: vals = vals[0]
            
            # A. Identificar la variable principal para la IA
            idx = np.argmax(np.abs(vals))
            var_shap = self.columnas_modelo[idx]
            
            # B. Construir el objeto JSON con TODAS las variables para el Front
            for col_name, impact_val in zip(self.columnas_modelo, vals):
                datos_grafica.append({
                    "variable": col_name,
                    "peso": round(float(impact_val), 4) # Convertir a float nativo para JSON
                })
            
            # C. Ordenar de mayor a menor impacto absoluto (para que la gráfica salga ordenada)
            datos_grafica = sorted(datos_grafica, key=lambda x: abs(x['peso']), reverse=True)

        # 4. IA Generativa
        salida_ia = {"resumen": "Normal", "factores": [], "recomendaciones": []}
        if self.usar_llm:
            salida_ia = self._generar_analisis_ia(contrato_json, indice_final, nivel_alerta, features, var_shap)

        return {
            "ID": contrato_json.get("ID Contrato", "S/N"),
            "Resumen_Ejecutivo": salida_ia.get("resumen"),
            "Factores_Principales": salida_ia.get("factores", []),
            "Recomendaciones_Auditor": salida_ia.get("recomendaciones", []),
            # AQUÍ ESTÁ LA NUEVA SECCIÓN PARA TU GRÁFICA
            "Detalle_SHAP": datos_grafica, 
            "Meta_Data": {
                "Riesgo": nivel_alerta,
                "Score": round(indice_final, 2)
            }
        }