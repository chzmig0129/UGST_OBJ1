"""
Utilidades para limpieza, parseo y clasificación de coordenadas geográficas.

Este módulo proporciona funciones para:
- Limpiar strings de coordenadas crudas
- Parsear coordenadas decimales con letras N/S/E/W
- Clasificar la calidad y viabilidad de coordenadas
"""

import re


def limpiar_coordenadas_raw(coord_str):
    """
    Pre-limpia el string de coordenadas ANTES de cualquier parseo.
    
    Pasos de limpieza:
    1. Strip leading/trailing whitespace
    2. Reemplaza \\n, \\r, \\t con string vacío
    3. Remueve texto trailing después del último par de coordenadas válido
    4. Remueve comillas dobles extra
    5. Arregla problemas de signos
    
    Args:
        coord_str (str): String de coordenadas crudo
        
    Returns:
        str: String de coordenadas limpio
    """
    if not coord_str:
        return ""
    
    # 1. Strip leading/trailing whitespace
    cleaned = coord_str.strip()
    
    # 2. Replace \n, \r, \t with empty string
    cleaned = cleaned.replace('\n', '').replace('\r', '').replace('\t', '')
    
    # 3. Remove trailing text after last valid coordinate pair
    # Pattern: after the last |-separated coordinate, if there's ",MAIZ BLANCO" or ",FRIJOL" etc., remove it
    # Use regex: r'["\']?\s*,\s*[A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,}\s*$'
    cleaned = re.sub(r'["\']?\s*,\s*[A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,}\s*$', '', cleaned)
    
    # 4. Remove extra double quotes ("" → ", standalone " that aren't part of DMS seconds)
    # First replace double quotes
    cleaned = cleaned.replace('""', '"')
    # Remove standalone quotes that aren't part of DMS (not preceded by a digit)
    # Be careful not to remove quotes that are part of DMS seconds notation
    # We'll keep quotes that follow digits (DMS seconds)
    
    # 5. Fix sign issues: .- → -, ,. → ,- (but be careful not to break decimal points)
    cleaned = cleaned.replace('.-', '-')
    # For ,. we need to be careful - only replace if followed by a minus sign pattern
    # Actually the pattern is: ",." should become ",-" when it's clearly a negative coordinate
    # Let's check if there's a digit after the dot
    cleaned = re.sub(r',\.(?=-)', ',-', cleaned)
    # Also handle the case where ,. is followed by a digit (should be ,-)
    cleaned = re.sub(r',\.(\d)', r',-\1', cleaned)
    
    return cleaned


def parsear_decimal_con_letra(coord_str):
    """
    Parsea coordenadas en formato decimal con letra direccional.
    
    Maneja formatos como:
    - 17.12656N,-101.75740
    - 17.12656N,-101.75740W
    
    Args:
        coord_str (str): String de un par de coordenadas
        
    Returns:
        str: String formateado "lat,lon" con 6 decimales, o None si no puede parsear
    """
    if not coord_str:
        return None
    
    # Pattern: (-?\d+\.?\d*)\s*([NSns])\s*,\s*(-?\d+\.?\d*)\s*([WEwe])?
    pattern = r'(-?\d+\.?\d*)\s*([NSns])\s*,\s*(-?\d+\.?\d*)\s*([WEwe])?'
    match = re.match(pattern, coord_str.strip())
    
    if not match:
        return None
    
    lat_num = float(match.group(1))
    lat_dir = match.group(2).upper()
    lon_num = float(match.group(3))
    lon_dir = match.group(4).upper() if match.group(4) else None
    
    # Apply negative sign if S or W
    if lat_dir == 'S':
        lat_num = -abs(lat_num)
    else:  # N
        lat_num = abs(lat_num)
    
    if lon_dir == 'W':
        lon_num = -abs(lon_num)
    elif lon_dir == 'E':
        lon_num = abs(lon_num)
    else:
        # If no direction specified for longitude and > 90, make it negative (Mexico convention)
        if lon_num > 90:
            lon_num = -lon_num
    
    # Return formatted string with 6 decimal places
    return f"{lat_num:.6f},{lon_num:.6f}"


def clasificar_coordenadas(coord_original, coord_procesada):
    """
    Clasifica la calidad y viabilidad de las coordenadas.
    
    Args:
        coord_original (str): String de coordenadas original sin procesar
        coord_procesada (str): String de coordenadas después de procesamiento
        
    Returns:
        tuple[str, str]: (status, detail_message)
            status puede ser: 'sin_coordenadas', 'utm_no_soportado', 
            'zonas_utm_inconsistentes', 'dms_compacto', 'error_conversion',
            'punto_unico', 'menos_3_vertices', 'ok'
    """
    # 1. Check if original is empty/None/whitespace
    if not coord_original or not coord_original.strip():
        return ('sin_coordenadas', 'No hay coordenadas registradas para este polígono.')
    
    # 2. Check for UTM pattern
    utm_pattern = r'\d{1,2}[A-Z]\d{5,}'
    if re.search(utm_pattern, coord_original):
        # Check if multiple different zones exist
        zones = re.findall(r'(\d{1,2}[A-Z])', coord_original)
        unique_zones = set(zones)
        if len(unique_zones) > 1:
            return ('zonas_utm_inconsistentes', 
                   'Las coordenadas UTM tienen zonas inconsistentes (ej: 14Q y 15Q en el mismo polígono). Requiere revisión manual.')
        else:
            return ('utm_no_soportado', 
                   'Las coordenadas están en formato UTM (ej: 13Q4846252399503). Este formato no está soportado actualmente. Puede dibujar el polígono manualmente.')
    
    # 3. Check for compact DMS without symbols
    dms_compacto_pattern = r'^\d{6}[NS],\d{7}[EW]'
    if re.search(dms_compacto_pattern, coord_original):
        return ('dms_compacto', 
               'Formato DMS compacto sin símbolos (ej: 202804N,1011056W). No soportado actualmente. Puede dibujar el polígono manualmente.')
    
    # 4. Check if processed coordinates are empty after processing
    if not coord_procesada or not coord_procesada.strip():
        # Get first 100 chars of original for error message
        orig_preview = coord_original[:100] if len(coord_original) > 100 else coord_original
        return ('error_conversion', 
               f'No se pudieron convertir las coordenadas a formato decimal. Coordenadas originales: {orig_preview}. Puede dibujar el polígono manualmente.')
    
    # 5. Count unique vertices
    vertices = [v.strip() for v in coord_procesada.split('|') if v.strip()]
    unique_vertices = list(set(vertices))
    
    # Check if all vertices are identical
    if len(unique_vertices) == 1 and len(vertices) > 1:
        return ('punto_unico', 
               'Todas las coordenadas apuntan al mismo lugar. No se puede formar un polígono. Puede dibujar el polígono manualmente.')
    
    # Check if less than 3 unique vertices
    if len(unique_vertices) < 3:
        n = len(unique_vertices)
        return ('menos_3_vertices', 
               f'Solo hay {n} vértice(s) único(s). Se necesitan mínimo 3 para formar un polígono. Puede dibujar el polígono manualmente.')
    
    # 6. Otherwise, coordinates are OK
    return ('ok', None)


def fue_limpiado(coord_original, coord_limpia):
    """
    Verifica si la función de limpieza modificó el string.
    
    Args:
        coord_original (str): String original
        coord_limpia (str): String después de limpieza
        
    Returns:
        bool: True si el string fue modificado, False si no
    """
    if coord_original is None and coord_limpia is None:
        return False
    if coord_original is None or coord_limpia is None:
        return True
    return coord_original != coord_limpia
