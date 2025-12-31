"""
Servicio de caché usando Turso (libSQL) para almacenar análisis de contratos.
Optimiza performance evitando re-análisis de contratos ya procesados.
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import libsql


class CacheService:
    """Servicio singleton para gestionar caché de análisis en Turso."""
    
    _instance = None
    _conn = None
    
    def __new__(cls):
        """Patrón Singleton para conexión única."""
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa conexión a Turso."""
        if self._conn is None:
            self._connect()
    
    def _connect(self):
        """Establece conexión con Turso usando variables de entorno."""
        try:
            url = os.getenv("TURSO_DATABASE_URL")
            auth_token = os.getenv("TURSO_AUTH_TOKEN")
            
            if not url or not auth_token:
                print("⚠️ TURSO_DATABASE_URL o TURSO_AUTH_TOKEN no configurados. Caché deshabilitado.")
                return
            
            self._conn = libsql.connect(url, auth_token=auth_token)
            print(f"✅ Conectado a Turso: {url}")
        except Exception as e:
            print(f"❌ Error conectando a Turso: {e}")
            self._conn = None
    
    @property
    def is_enabled(self) -> bool:
        """Verifica si el caché está habilitado."""
        return self._conn is not None
    
    def _get_ttl_days(self, tipo: str) -> int:
        """Obtiene TTL en días según tipo de caché."""
        defaults = {"stats": 1, "ligero": 7, "detallado": 7}
        env_key = f"CACHE_TTL_{tipo.upper()}"
        return int(os.getenv(env_key, defaults.get(tipo, 7)))
    
    def _calculate_expiration(self, tipo: str) -> str:
        """Calcula fecha de expiración según TTL."""
        days = self._get_ttl_days(tipo)
        expiration = datetime.now() + timedelta(days=days)
        return expiration.isoformat()
    
    @staticmethod
    def generate_filter_hash(filters: Dict[str, Any]) -> str:
        """Genera hash único para combinación de filtros."""
        # Ordenar filtros para hash consistente
        filter_str = json.dumps(filters, sort_keys=True)
        return hashlib.md5(filter_str.encode()).hexdigest()
    
    # ==================== ESTADÍSTICAS GLOBALES ====================
    
    def get_estadisticas_cached(self, filtro_hash: str) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas globales del caché si existen y son válidas."""
        if not self.is_enabled:
            return None
        
        try:
            query = """
                SELECT total_contratos, contratos_alto_riesgo, 
                       contratos_medio_riesgo, contratos_bajo_riesgo,
                       porcentaje_alto_riesgo, monto_total_cop
                FROM estadisticas_globales
                WHERE filtro_hash = ? 
                  AND fecha_expiracion > ?
                LIMIT 1
            """
            now = datetime.now().isoformat()
            result = self._conn.execute(query, (filtro_hash, now)).fetchone()
            
            if result:
                print(f"✅ Cache HIT: Estadísticas globales (hash: {filtro_hash[:8]}...)")
                return {
                    "total_contratos": result[0],
                    "contratos_alto_riesgo": result[1],
                    "contratos_medio_riesgo": result[2],
                    "contratos_bajo_riesgo": result[3],
                    "porcentaje_alto_riesgo": result[4],
                    "monto_total_cop": result[5]
                }
            
            print(f"❌ Cache MISS: Estadísticas globales (hash: {filtro_hash[:8]}...)")
            return None
        except Exception as e:
            print(f"❌ Error leyendo estadísticas: {e}")
            return None
    
    def save_estadisticas(
        self, 
        filtro_hash: str,
        filtro_descripcion: str,
        total_contratos: int,
        contratos_alto_riesgo: int,
        contratos_medio_riesgo: int,
        contratos_bajo_riesgo: int,
        porcentaje_alto_riesgo: float,
        monto_total_cop: float
    ):
        """Guarda estadísticas globales en caché."""
        if not self.is_enabled:
            return
        
        try:
            expiracion = self._calculate_expiration("stats")
            
            query = """
                INSERT OR REPLACE INTO estadisticas_globales (
                    filtro_hash, filtro_descripcion, total_contratos,
                    contratos_alto_riesgo, contratos_medio_riesgo, contratos_bajo_riesgo,
                    porcentaje_alto_riesgo, monto_total_cop, fecha_expiracion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self._conn.execute(query, (
                filtro_hash, filtro_descripcion, total_contratos,
                contratos_alto_riesgo, contratos_medio_riesgo, contratos_bajo_riesgo,
                porcentaje_alto_riesgo, monto_total_cop, expiracion
            ))
            self._conn.commit()
            
            print(f"💾 Estadísticas guardadas (hash: {filtro_hash[:8]}..., {total_contratos} contratos)")
        except Exception as e:
            print(f"❌ Error guardando estadísticas: {e}")
    
    # ==================== ANÁLISIS LIGERO ====================
    
    def get_analisis_ligero(self, id_contrato: str) -> Optional[Dict[str, Any]]:
        """Obtiene análisis ligero de un contrato del caché."""
        if not self.is_enabled:
            return None
        
        try:
            query = """
                SELECT nombre_entidad, valor_contrato, fecha_inicio,
                       nivel_riesgo, anomalia, score_isolation_forest, score_nlp_embeddings
                FROM contratos_analisis_ligero
                WHERE id_contrato = ? AND fecha_expiracion > ?
            """
            now = datetime.now().isoformat()
            result = self._conn.execute(query, (id_contrato, now)).fetchone()
            
            if result:
                return {
                    "nombre_entidad": result[0],
                    "valor_contrato": result[1],
                    "fecha_inicio": result[2],
                    "nivel_riesgo": result[3],
                    "anomalia": result[4],
                    "score_isolation_forest": result[5],
                    "score_nlp_embeddings": result[6]
                }
            return None
        except Exception as e:
            print(f"❌ Error leyendo análisis ligero: {e}")
            return None
    
    def get_analisis_ligero_batch(self, ids_contratos: List[str]) -> Dict[str, Dict[str, Any]]:
        """Obtiene múltiples análisis ligeros en batch."""
        if not self.is_enabled or not ids_contratos:
            return {}
        
        try:
            placeholders = ",".join("?" * len(ids_contratos))
            query = f"""
                SELECT id_contrato, nombre_entidad, valor_contrato, fecha_inicio,
                       nivel_riesgo, anomalia, score_isolation_forest, score_nlp_embeddings
                FROM contratos_analisis_ligero
                WHERE id_contrato IN ({placeholders}) AND fecha_expiracion > ?
            """
            
            now = datetime.now().isoformat()
            params = ids_contratos + [now]
            results = self._conn.execute(query, params).fetchall()
            
            cached = {}
            for row in results:
                cached[row[0]] = {
                    "nombre_entidad": row[1],
                    "valor_contrato": row[2],
                    "fecha_inicio": row[3],
                    "nivel_riesgo": row[4],
                    "anomalia": row[5],
                    "score_isolation_forest": row[6],
                    "score_nlp_embeddings": row[7]
                }
            
            print(f"✅ Cache HIT: {len(cached)}/{len(ids_contratos)} análisis ligeros")
            return cached
        except Exception as e:
            print(f"❌ Error en batch ligero: {e}")
            return {}
    
    def save_analisis_ligero(
        self,
        id_contrato: str,
        nombre_entidad: str,
        valor_contrato: float,
        fecha_inicio: str,
        nivel_riesgo: str,
        anomalia: float,
        score_isolation_forest: Optional[float] = None,
        score_nlp_embeddings: Optional[float] = None
    ):
        """Guarda análisis ligero en caché."""
        if not self.is_enabled:
            return
        
        try:
            expiracion = self._calculate_expiration("ligero")
            
            query = """
                INSERT OR REPLACE INTO contratos_analisis_ligero (
                    id_contrato, nombre_entidad, valor_contrato, fecha_inicio,
                    nivel_riesgo, anomalia, score_isolation_forest, score_nlp_embeddings,
                    fecha_expiracion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self._conn.execute(query, (
                id_contrato, nombre_entidad, valor_contrato, fecha_inicio,
                nivel_riesgo, anomalia, score_isolation_forest, score_nlp_embeddings,
                expiracion
            ))
            self._conn.commit()
        except Exception as e:
            print(f"❌ Error guardando análisis ligero {id_contrato}: {e}")
    
    def save_analisis_ligero_batch(self, analisis_list: List[Dict[str, Any]]):
        """Guarda múltiples análisis ligeros en batch."""
        if not self.is_enabled or not analisis_list:
            return
        
        try:
            expiracion = self._calculate_expiration("ligero")
            
            query = """
                INSERT OR REPLACE INTO contratos_analisis_ligero (
                    id_contrato, nombre_entidad, valor_contrato, fecha_inicio,
                    nivel_riesgo, anomalia, score_isolation_forest, score_nlp_embeddings,
                    fecha_expiracion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            for analisis in analisis_list:
                self._conn.execute(query, (
                    analisis.get("id_contrato"),
                    analisis.get("nombre_entidad"),
                    analisis.get("valor_contrato"),
                    analisis.get("fecha_inicio"),
                    analisis.get("nivel_riesgo"),
                    analisis.get("anomalia"),
                    analisis.get("score_isolation_forest"),
                    analisis.get("score_nlp_embeddings"),
                    expiracion
                ))
            
            self._conn.commit()
            print(f"💾 {len(analisis_list)} análisis ligeros guardados en batch")
        except Exception as e:
            print(f"❌ Error en batch save ligero: {e}")
    
    # ==================== ANÁLISIS DETALLADO ====================
    
    def get_analisis_detallado(self, id_contrato: str) -> Optional[Dict[str, Any]]:
        """Obtiene análisis detallado del caché."""
        if not self.is_enabled:
            return None
        
        try:
            query = """
                SELECT resumen_ejecutivo, factores_principales, recomendaciones,
                       shap_values, score_final, score_isolation_forest, 
                       score_nlp_embeddings, isolation_forest_raw, 
                       distancia_semantica, meta_data
                FROM contratos_analisis_detallado
                WHERE id_contrato = ? AND fecha_expiracion > ?
            """
            now = datetime.now().isoformat()
            result = self._conn.execute(query, (id_contrato, now)).fetchone()
            
            if result:
                print(f"✅ Cache HIT: Análisis detallado ({id_contrato})")
                return {
                    "resumen_ejecutivo": result[0],
                    "factores_principales": json.loads(result[1]) if result[1] else [],
                    "recomendaciones": json.loads(result[2]) if result[2] else [],
                    "shap_values": json.loads(result[3]) if result[3] else [],
                    "score_final": result[4],
                    "score_isolation_forest": result[5],
                    "score_nlp_embeddings": result[6],
                    "isolation_forest_raw": result[7],
                    "distancia_semantica": result[8],
                    "meta_data": json.loads(result[9]) if result[9] else {}
                }
            
            print(f"❌ Cache MISS: Análisis detallado ({id_contrato})")
            return None
        except Exception as e:
            print(f"❌ Error leyendo análisis detallado: {e}")
            return None
    
    def save_analisis_detallado(
        self,
        id_contrato: str,
        resumen_ejecutivo: str,
        factores_principales: List[str],
        recomendaciones: List[str],
        shap_values: List[Dict[str, Any]],
        score_final: float,
        score_isolation_forest: float,
        score_nlp_embeddings: float,
        isolation_forest_raw: float,
        distancia_semantica: float,
        meta_data: Dict[str, Any],
        duracion_analisis_ms: int = 0
    ):
        """Guarda análisis detallado en caché."""
        if not self.is_enabled:
            return
        
        try:
            expiracion = self._calculate_expiration("detallado")
            
            query = """
                INSERT OR REPLACE INTO contratos_analisis_detallado (
                    id_contrato, resumen_ejecutivo, factores_principales, recomendaciones,
                    shap_values, score_final, score_isolation_forest, score_nlp_embeddings,
                    isolation_forest_raw, distancia_semantica, meta_data, 
                    fecha_expiracion, duracion_analisis_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self._conn.execute(query, (
                id_contrato,
                resumen_ejecutivo,
                json.dumps(factores_principales),
                json.dumps(recomendaciones),
                json.dumps(shap_values),
                score_final,
                score_isolation_forest,
                score_nlp_embeddings,
                isolation_forest_raw,
                distancia_semantica,
                json.dumps(meta_data),
                expiracion,
                duracion_analisis_ms
            ))
            self._conn.commit()
            
            print(f"💾 Análisis detallado guardado ({id_contrato})")
        except Exception as e:
            print(f"❌ Error guardando análisis detallado: {e}")
    
    # ==================== UTILIDADES ====================
    
    def cleanup_expired(self):
        """Elimina registros expirados de todas las tablas."""
        if not self.is_enabled:
            return
        
        try:
            now = datetime.now().isoformat()
            
            tables = ["estadisticas_globales", "contratos_analisis_ligero", "contratos_analisis_detallado"]
            for table in tables:
                result = self._conn.execute(
                    f"DELETE FROM {table} WHERE fecha_expiracion <= ?",
                    (now,)
                )
                self._conn.commit()
                print(f"🧹 Limpieza {table}: registros eliminados")
        except Exception as e:
            print(f"❌ Error en cleanup: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del caché."""
        if not self.is_enabled:
            return {}
        
        try:
            stats = {}
            tables = {
                "estadisticas_globales": "total_stats",
                "contratos_analisis_ligero": "total_ligero",
                "contratos_analisis_detallado": "total_detallado"
            }
            
            for table, key in tables.items():
                result = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats[key] = result[0] if result else 0
            
            return stats
        except Exception as e:
            print(f"❌ Error obteniendo stats: {e}")
            return {}
    
    def close(self):
        """Cierra la conexión a Turso."""
        if self._conn:
            self._conn.close()
            print("🔌 Conexión a Turso cerrada")
            self._conn = None


# Instancia global singleton
cache_service = CacheService()
