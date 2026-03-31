"""
Spatial validation engine: compares loaded polygons against the megacapa.
"""
import geopandas as gpd
from shapely.geometry import Polygon as ShapelyPolygon
from utils.shapefile_cache import shp_cache
from utils.geometry import ordenar_coordenadas


def construir_geometria(coordenadas_corregidas):
    """
    Build a Shapely Polygon from coordenadas_corregidas string.
    Format: 'lat,lon | lat,lon | lat,lon | ...'
    Returns (geometry, error_string) tuple.
    geometry is None if it can't be built.
    """
    if not coordenadas_corregidas or not coordenadas_corregidas.strip():
        return None, 'sin_coordenadas'

    try:
        # Ordenar coordenadas para evitar auto-intersecciones
        coordenadas_ordenadas = ordenar_coordenadas(coordenadas_corregidas)
        pairs = coordenadas_ordenadas.split(' | ')
        coords = []
        for pair in pairs:
            pair = pair.strip()
            if ',' not in pair:
                continue
            parts = pair.split(',')
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            coords.append((lon, lat))  # Shapely uses (x=lon, y=lat)

        if len(coords) < 3:
            return None, 'puntos_insuficientes'

        # Close the polygon if not already closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        geom = ShapelyPolygon(coords)
        if not geom.is_valid:
            geom = geom.buffer(0)  # Fix self-intersections
        if geom.is_empty:
            return None, 'geometria_vacia'

        return geom, None
    except Exception as e:
        return None, f'error: {str(e)}'


def ejecutar_validacion_megacapa(poligonos, umbral_traslape=85.0):
    """
    Compare a list of Poligono ORM objects against the megacapa shapefile.

    Args:
        poligonos: list of Poligono model instances (must have .id, .id_poligono, .id_credito, .coordenadas_corregidas)
        umbral_traslape: minimum overlap percentage to classify as VINCULAR (default 85%)

    Returns:
        list of dicts, one per polígono, each with keys:
            poligono_id, id_poligono, id_credito, estatus_megacapa,
            id_poligono_unico, porcentaje_traslape, id_credito_megacapa, motivo
    """
    # Load megacapa (cached singleton)
    mega = shp_cache.mega
    sindex = mega.sindex

    resultados = []

    for poligono in poligonos:
        geom, error = construir_geometria(poligono.coordenadas_corregidas)

        if geom is None:
            resultados.append({
                'poligono_id': poligono.id,
                'id_poligono': poligono.id_poligono,
                'id_credito': poligono.id_credito,
                'estatus_megacapa': 'NUEVO',
                'id_poligono_unico': None,
                'porcentaje_traslape': None,
                'id_credito_megacapa': None,
                'motivo': error,
            })
            continue

        # Query spatial index for candidates
        candidates = list(sindex.intersection(geom.bounds))

        best_overlap = 0.0
        best_id_poligon = None
        best_id_credito = None

        for idx in candidates:
            mega_row = mega.iloc[idx]
            mega_geom = mega_row.geometry

            if mega_geom is None or mega_geom.is_empty:
                continue

            try:
                if not geom.intersects(mega_geom):
                    continue

                intersection_area = geom.intersection(mega_geom).area
                if geom.area > 0:
                    overlap_pct = (intersection_area / geom.area) * 100
                else:
                    overlap_pct = 0.0

                if overlap_pct > best_overlap:
                    best_overlap = overlap_pct
                    best_id_poligon = mega_row['ID_POLIGON']
                    best_id_credito = str(mega_row['ID_CREDITO'])
            except Exception:
                continue

        if best_overlap >= umbral_traslape:
            resultados.append({
                'poligono_id': poligono.id,
                'id_poligono': poligono.id_poligono,
                'id_credito': poligono.id_credito,
                'estatus_megacapa': 'VINCULAR',
                'id_poligono_unico': best_id_poligon,
                'porcentaje_traslape': round(best_overlap, 2),
                'id_credito_megacapa': best_id_credito,
                'motivo': f'traslape>={umbral_traslape}%',
            })
        else:
            resultados.append({
                'poligono_id': poligono.id,
                'id_poligono': poligono.id_poligono,
                'id_credito': poligono.id_credito,
                'estatus_megacapa': 'NUEVO',
                'id_poligono_unico': best_id_poligon if best_overlap > 0 else None,
                'porcentaje_traslape': round(best_overlap, 2) if best_overlap > 0 else None,
                'id_credito_megacapa': best_id_credito if best_overlap > 0 else None,
                'motivo': f'traslape<{umbral_traslape}%' if best_overlap > 0 else 'sin_traslape',
            })

    return resultados
