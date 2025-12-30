import joblib
import json
import numpy as np
import pandas as pd
from groq import Groq
from sentence_transformers import SentenceTransformer
import time
import os

class RadarColInferencia:
    def __init__(self, groq_api_key=None, ruta_artefactos="data/artefactos"):
        try:
            print(f"Inicializando Motor RadarCol (V2.5 + Datos Graficos)...")
        except:
            print("Inicializando Motor RadarCol...")
        
        # 1. Configurar Cliente Groq (LLM API Gratuita)
        self.usar_llm = False
        self.client = None
        self.model_name = "llama-3.1-8b-instant"  # Modelo rápido y eficiente para Render
        
        try:
            if groq_api_key:
                self.client = Groq(api_key=groq_api_key)
            else:
                # Intenta usar variable de entorno GROQ_API_KEY
                self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            self.usar_llm = True
            print(f"   [OK] Cliente Groq conectado ({self.model_name}).")
            print(f"   [INFO] Free tier: 30 req/min, 14.4k req/día")
        except Exception as e:
            print(f"   [WARN] Error inicializando cliente Groq: {e}")
            print(f"   [INFO] Motor continuará sin análisis LLM (solo ML)")

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
        """Genera respuesta usando Groq API con reintentos."""
        intentos = 3
        for i in range(intentos):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un auditor forense experto en contratación pública. Respondes SOLO con JSON válido."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Más determinista para análisis técnico
                    max_tokens=800,   # Suficiente para análisis completo
                    response_format={"type": "json_object"}  # Forzar respuesta JSON
                )
                return response.choices[0].message.content
            except Exception as e:
                err = str(e)
                if "429" in err or "rate_limit" in err.lower():
                    wait_time = 12 + (i * 5)
                    print(f"   [WARN] Rate limit alcanzado. Esperando {wait_time}s...")
                    time.sleep(wait_time)
                elif "quota" in err.lower():
                    print(f"   [ERROR] Cuota de Groq agotada. Motor continuará sin LLM.")
                    break
                else:
                    print(f"   [ERROR] Groq API error: {err}")
                    break
        return None

    def _generar_analisis_ia(self, contrato, riesgo, nivel, features, var_shap, shap_values=None, score_ml=0.5, score_nlp=0.5, raw_iforest=None, distancia_sem=None):
        # Definir interpretaciones en lenguaje natural
        if score_ml > 0.7:
            interpretacion_ml = "ALTO"
        elif score_ml > 0.5:
            interpretacion_ml = "MEDIO"
        else:
            interpretacion_ml = "BAJO"
        
        if score_nlp > 0.6:
            interpretacion_nlp = "muy diferente"
        elif score_nlp > 0.4:
            interpretacion_nlp = "moderadamente diferente"
        else:
            interpretacion_nlp = "similar"
        
        # Construir sección de análisis SHAP para el prompt (en lenguaje simple)
        shap_info = ""
        if shap_values and len(shap_values) > 0:
            shap_info = "\n        ANÁLISIS DE FACTORES CLAVE (Interpretación para el LLM):\n"
            for i, item in enumerate(shap_values[:5], 1):  # Top 5 variables
                variable = item.get('variable', 'N/A')
                peso = item.get('peso', 0)
                direccion = "aumenta" if peso > 0 else "disminuye"
                intensidad = "fuertemente" if abs(peso) > 0.3 else "moderadamente" if abs(peso) > 0.1 else "levemente"
                shap_info += f"        {i}. {variable}: {peso:.4f} ({intensidad} {direccion} el riesgo)\n"
        
        prompt = f"""
        Eres un Auditor Forense que explica hallazgos a personas SIN conocimientos técnicos (alcaldes, concejales, ciudadanos).
        
        DATOS DEL CONTRATO:
        - ID: {contrato.get('ID Contrato', 'N/A')}
        - Descripción: "{contrato.get('Objeto del Contrato')}"
        - Valor: ${contrato.get('Valor del Contrato', 0):,.0f} COP (${contrato.get('Valor del Contrato', 0)/1000000:.1f} millones)
        - Entidad: {contrato.get('Nit Entidad')}
        - Duración: {contrato.get('Duracion Dias', 0)} días ({contrato.get('Duracion Dias', 0)/30:.1f} meses aprox.)
        
        RESULTADO DE LOS MODELOS DE ANÁLISIS:
        
        1. DETECTOR DE ANOMALÍAS (IsolationForest): {score_ml:.2%}
           Interpretación: Este modelo detectó un nivel {interpretacion_ml} de anomalía en los valores numéricos del contrato.
           {"Esto significa que el contrato tiene características inusuales comparado con contratos similares." if score_ml > 0.6 else "Los valores del contrato están dentro de rangos normales."}
        
        2. ANÁLISIS SEMÁNTICO (Embeddings): {score_nlp:.2%}
           Interpretación: La descripción del contrato es {interpretacion_nlp} respecto a contratos habituales.
           {"El texto sugiere un tipo de proyecto poco común para esta entidad." if score_nlp > 0.5 else "El tipo de proyecto es típico para este tipo de entidad."}
        
        3. Z-SCORE DEL VALOR: {features['Z-Score Valor']:.2f}
           {"⚠️ CRÍTICO: El monto está " + str(abs(features['Z-Score Valor'])) + " veces por encima del promedio histórico de la entidad." if features['Z-Score Valor'] > 2 else "El monto está dentro de rangos esperados para esta entidad."}
        
        4. NIVEL DE RIESGO FINAL: {nivel} ({riesgo:.0%})
        {shap_info}
        
        INSTRUCCIONES CRÍTICAS:
        1. USA LENGUAJE SIMPLE Y COTIDIANO - Evita términos técnicos como "Z-Score", "embeddings", "SHAP", "IsolationForest"
        2. USA ANALOGÍAS Y COMPARACIONES - Ejemplo: "como si compraras un pan por el precio de 10 panes"
        3. EXPLICA EL "POR QUÉ ES ANÓMALO" en términos que cualquier persona entienda
        4. FACTORES: Describe cada factor clave en lenguaje sencillo, explicando su impacto real
        5. RECOMENDACIONES: Acciones concretas y comprensibles para funcionarios no técnicos
        6. Los arrays "factores" y "recomendaciones" DEBEN contener SOLO STRINGS SIMPLES
        
        EJEMPLOS DE LENGUAJE SIMPLE:
        ❌ MAL: "El Z-Score de 3.5 indica una desviación estándar significativa"
        ✅ BIEN: "El precio de este contrato es 3.5 veces más alto que el promedio que esta entidad suele pagar por contratos similares"
        
        ❌ MAL: "El score del IsolationForest es 0.82"
        ✅ BIEN: "Nuestro sistema de detección de anomalías encontró que este contrato tiene características muy distintas al 82% de contratos normales"
        
        FORMATO JSON REQUERIDO:
        {{
            "resumen": "Explicación clara y directa de por qué este contrato es sospechoso (o normal). Usa lenguaje simple, menciona cifras concretas en millones de pesos, compara con promedios. Máximo 3-4 oraciones cortas.",
            
            "factores": [
                "El precio del contrato es [X] veces más alto que el promedio habitual de esta entidad, lo que sugiere posible sobrecosto",
                "La relación entre el precio y la complejidad del trabajo es inusual: se está pagando mucho dinero por una descripción de trabajo relativamente simple",
                "La duración del contrato combinada con el monto resulta en un costo diario muy elevado comparado con contratos similares",
                "[Otro factor en lenguaje simple]"
            ],
            
            "recomendaciones": [
                "Solicitar una justificación detallada de por qué este contrato cuesta [X] millones más que el promedio de contratos similares",
                "Comparar este contrato con al menos 3 contratos similares ejecutados por la misma entidad en los últimos 2 años",
                "Revisar si existe un estudio de mercado que respalde el precio contratado",
                "[Otra acción concreta y entendible]"
            ]
        }}
        
        RECUERDA: Tu audiencia son ciudadanos, periodistas, y funcionarios NO técnicos. Sé claro, directo y evita jerga técnica
                "Recomendación 3 de seguimiento"
            ]
        }}
        
        IMPORTANTE: factores y recomendaciones deben ser arrays de strings, NO objetos.
        """
        texto = self._generar_con_retry(prompt)
        if texto:
            try:
                resultado = json.loads(texto.replace("```json", "").replace("```", "").strip())
                
                # Validación y conversión robusta de factores
                if "factores" in resultado:
                    factores_limpios = []
                    for item in resultado["factores"]:
                        if isinstance(item, str):
                            factores_limpios.append(item)
                        elif isinstance(item, dict):
                            # Si el LLM devolvió un objeto, convertirlo a string
                            if "descripcion" in item:
                                factores_limpios.append(item["descripcion"])
                            elif "variable" in item and "impacto" in item:
                                factores_limpios.append(f"{item['variable']}: {item['impacto']}")
                            else:
                                # Concatenar todos los valores del dict
                                factores_limpios.append(" - ".join(str(v) for v in item.values()))
                    resultado["factores"] = factores_limpios
                
                # Validación y conversión robusta de recomendaciones
                if "recomendaciones" in resultado:
                    recom_limpias = []
                    for item in resultado["recomendaciones"]:
                        if isinstance(item, str):
                            recom_limpias.append(item)
                        elif isinstance(item, dict):
                            # Si el LLM devolvió un objeto, convertirlo a string
                            if "accion" in item:
                                recom_limpias.append(item["accion"])
                            elif "recomendacion" in item:
                                recom_limpias.append(item["recomendacion"])
                            else:
                                recom_limpias.append(" - ".join(str(v) for v in item.values()))
                    resultado["recomendaciones"] = recom_limpias
                
                return resultado
            except Exception as e:
                print(f"   [ERROR] Error parseando respuesta LLM: {e}")
                pass
        return {"resumen": "Error IA", "factores": [], "recomendaciones": []}

    def analizar_contrato(self, contrato_json):
        X, texto, features = self._preprocesar(contrato_json)
        
        # 1. ML Score (IsolationForest)
        risk_ml = 0.95
        score_raw_iforest = None
        if self.iso_forest:
            score_raw_iforest = self.iso_forest.decision_function(X)[0]
            risk_ml = float(np.clip(1 - ((score_raw_iforest - (-0.5)) / (0.5 - (-0.5))), 0, 1))
        
        if features["Z-Score Valor"] > 3: risk_ml = 1.0
        
        # 2. NLP Score (Embeddings semánticos)
        risk_nlp = 0.5
        distancia_semantica = None
        if hasattr(self, 'model_nlp') and self.model_nlp:
             emb = self.model_nlp.encode(texto[:200], convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
             c = self.centroide if hasattr(self, 'centroide') else np.zeros(emb.shape)
             distancia_semantica = float(np.linalg.norm(emb - c))
             risk_nlp = float(np.clip(distancia_semantica / 1.2, 0, 1))

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

        # 4. IA Generativa con valores SHAP y metadata completa
        salida_ia = {"resumen": "Normal", "factores": [], "recomendaciones": []}
        if self.usar_llm:
            salida_ia = self._generar_analisis_ia(
                contrato_json, 
                indice_final, 
                nivel_alerta, 
                features, 
                var_shap,
                shap_values=datos_grafica,  # Valores SHAP completos
                score_ml=risk_ml,            # Score IsolationForest
                score_nlp=risk_nlp,          # Score NLP/Embeddings
                raw_iforest=score_raw_iforest,  # Raw score
                distancia_sem=distancia_semantica  # Distancia semántica
            )

        return {
            "ID": contrato_json.get("ID Contrato", "S/N"),
            "Resumen_Ejecutivo": salida_ia.get("resumen"),
            "Factores_Principales": salida_ia.get("factores", []),
            "Recomendaciones_Auditor": salida_ia.get("recomendaciones", []),
            # AQUÍ ESTÁ LA NUEVA SECCIÓN PARA TU GRÁFICA
            "Detalle_SHAP": datos_grafica, 
            "Meta_Data": {
                "Riesgo": nivel_alerta,
                "Score": round(indice_final, 2),
                # Scores individuales de cada modelo
                "Score_IsolationForest": round(risk_ml, 4),
                "Score_NLP_Embeddings": round(risk_nlp, 4),
                # Valores técnicos raw (para debugging/análisis avanzado)
                "IsolationForest_Raw": round(float(score_raw_iforest), 4) if score_raw_iforest is not None else None,
                "Distancia_Semantica": round(float(distancia_semantica), 4) if distancia_semantica is not None else None,
                # Pesos del ensemble
                "Pesos_Ensemble": {
                    "ML": 0.5,
                    "NLP": 0.5
                },
                # Información del modelo NLP
                "Modelo_NLP": "hiiamsid/sentence_similarity_spanish_es" if hasattr(self, 'model_nlp') and self.model_nlp else None
            }
        }