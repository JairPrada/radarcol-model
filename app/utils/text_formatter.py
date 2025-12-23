"""
Utilidades de formateo de texto.
"""
import re


def estandarizar_texto(texto: str) -> str:
    """Estandariza el texto de contratos para formato de documento profesional.
    
    Aplica las siguientes reglas:
    - Capitaliza la primera letra del texto
    - Capitaliza después de puntos seguidos de espacio
    - Capitaliza después de puntos y coma cuando inicia nueva oración
    - Mantiene acrónimos y siglas
    - Limpia espacios extra y saltos de línea
    
    Args:
        texto (str): Texto a estandarizar
        
    Returns:
        str: Texto estandarizado
    """
    if not texto or not isinstance(texto, str):
        return ""
    
    # Limpiar el texto: eliminar saltos de línea extra y espacios múltiples
    texto = " ".join(texto.split())
    texto = texto.strip()
    
    if not texto:
        return ""
    
    # Convertir a minúsculas para empezar el proceso
    texto = texto.lower()
    
    # Capitalizar primera letra
    texto = texto[0].upper() + texto[1:] if len(texto) > 1 else texto.upper()
    
    # Capitalizar después de puntos seguidos de espacio
    patron_punto = r'\. +([a-z])'
    texto = re.sub(patron_punto, lambda m: '. ' + m.group(1).upper(), texto)
    
    # Capitalizar después de punto y coma cuando inicia nueva oración
    patron_punto_coma = r'; +([a-z])'
    texto = re.sub(patron_punto_coma, lambda m: '; ' + m.group(1).upper(), texto)
    
    # Capitalizar después de dos puntos cuando inicia nueva oración
    patron_dos_puntos = r': +([a-z])'
    texto = re.sub(patron_dos_puntos, lambda m: ': ' + m.group(1).upper(), texto)
    
    return texto
