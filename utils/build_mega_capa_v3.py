"""
utils/build_mega_capa_v3.py — Builder para Mega Capa V3.

Genera la tabla mega_capa_v3 y el shapefile data/MEGA_CAPA_V3.shp uniendo:
  - MEGA_CAPA_V2.shp  (fuente='v2',        ~62,625 features)
  - Poligono.estatus='7' neto (fuente='status7', ~3,740 features)
  - ValidacionDiciembre.estatus_validacion='NUEVO' via capa_diciembre (fuente='nuevo_dic', ~1,123 features)

IMPORTANTE: todos los imports SQLAlchemy/Flask se hacen dentro de la funcion
(lazy imports) para evitar el ciclo de importacion circular con app.py.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon


# ---------------------------------------------------------------------------
# Helpers de parseo de coordenadas
# ---------------------------------------------------------------------------

def _parse_coords_to_polygon(coord_str):
    """Convierte 'lat,lon | lat,lon | ...' a Shapely Polygon o None si invalido."""
    if not coord_str or not coord_str.strip():
        return None
    pts = []
    for p in coord_str.split(' | '):
        p = p.strip()
        if not p:
            continue
        parts = p.split(',')
        if len(parts) < 2:
            continue
        try:
            lat = float(parts[0])
            lon = float(parts[1])
        except ValueError:
            continue
        pts.append((lon, lat))  # Shapely usa (x=lon, y=lat)
    if len(pts) < 3:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    try:
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)  # arregla auto-intersecciones
        return poly if poly.is_valid and not poly.is_empty else None
    except Exception:
        return None


def _polygon_to_coord_str(geom):
    """Convierte geometria Shapely a 'lat,lon | lat,lon | ...' o None si invalida."""
    if geom is None or geom.is_empty:
        return None
    # MultiPolygon: tomar el mas grande
    if geom.geom_type == 'MultiPolygon':
        geom = max(geom.geoms, key=lambda g: g.area)
    if geom.geom_type != 'Polygon':
        return None
    coords = list(geom.exterior.coords)
    return ' | '.join(f'{y},{x}' for x, y in coords)


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def build_mega_capa_v3():
    """
    Construye Mega Capa V3: trunca la tabla, inserta filas de V2 + status7 + nuevo_dic,
    genera data/MEGA_CAPA_V3.shp y recarga el cache.

    Retorna dict con contadores:
      {'v2': N1, 'status7': N2, 'nuevo_dic': N3, 'total': N1+N2+N3,
       'status7_skipped': K1, 'nuevo_dic_skipped': K2}
    """
    # ------------------------------------------------------------------
    # Lazy imports para evitar ciclo circular con app.py
    # ------------------------------------------------------------------
    from extensions import db
    from models.mega_capa_v3 import MegaCapaV3
    from models.validacion_diciembre import ValidacionDiciembre
    from models.capa_diciembre import CapaDiciembre
    from models.validacion_megacapa import ValidacionMegacapa
    from models.segunda_validacion_poligono import SegundaValidacionPoligono
    from app import Poligono
    from utils.shapefile_cache import shp_cache

    # ------------------------------------------------------------------
    # a) TRUNCATE tabla mega_capa_v3
    # ------------------------------------------------------------------
    db.session.query(MegaCapaV3).delete()
    db.session.commit()

    rows = []          # dicts para bulk_insert_mappings
    geom_list = []     # geometrias Shapely para el shapefile
    id_poligon_list = []
    id_credito_list = []
    fuente_list = []

    # ------------------------------------------------------------------
    # b) FUENTE V2: leer desde shp_cache.mega (GeoDataFrame)
    # ------------------------------------------------------------------
    mega_gdf = shp_cache.mega  # GeoDataFrame con ID_POLIGON, ID_CREDITO, geometry

    count_v2 = 0
    for _, row in mega_gdf.iterrows():
        geom = row['geometry']
        id_poligono_unico = str(row['ID_POLIGON']) if pd.notna(row['ID_POLIGON']) else None
        id_credito = str(row['ID_CREDITO']) if pd.notna(row['ID_CREDITO']) else None

        # Construir texto de coordenadas desde la geometria del shapefile
        coord_str = _polygon_to_coord_str(geom)
        if coord_str is None:
            # Geometria invalida — intentar con el primer poligono si es MultiPolygon
            if geom is not None and geom.geom_type == 'MultiPolygon':
                coord_str = _polygon_to_coord_str(geom.geoms[0])
        if coord_str is None:
            continue  # skip si no se pudo generar texto de coordenadas

        rows.append({
            'id_poligono_unico': id_poligono_unico,
            'id_credito': id_credito,
            'fuente': 'v2',
            'coordenadas': coord_str,
        })

        # Guardar geometria original para el shapefile de salida
        geom_list.append(geom)
        id_poligon_list.append(id_poligono_unico)
        id_credito_list.append(id_credito)
        fuente_list.append('v2')

        count_v2 += 1

    # ------------------------------------------------------------------
    # c) FUENTE status7: Poligono.estatus='7' con exclusiones
    # ------------------------------------------------------------------
    # Exclusiones identicas a _build_universo_combinado() en utils/validacion_diciembre.py
    vinc_megacapa = set(
        v.poligono_id
        for v in ValidacionMegacapa.query.filter_by(estatus_megacapa='VINCULAR').all()
    )
    seg_val = set(
        s.poligono_id
        for s in SegundaValidacionPoligono.query.filter(
            SegundaValidacionPoligono.decision.in_(['ELIMINAR', 'VINCULAR'])
        ).all()
    )
    excluir = vinc_megacapa | seg_val

    poligonos_7 = Poligono.query.filter(Poligono.estatus == '7').all()
    poligonos_7_netos = [p for p in poligonos_7 if p.id not in excluir]

    count_status7 = 0
    skip_status7 = 0
    for p in poligonos_7_netos:
        coord_str = p.coordenadas_corregidas
        geom = _parse_coords_to_polygon(coord_str)
        if geom is None:
            skip_status7 += 1
            continue

        rows.append({
            'id_poligono_unico': p.id_poligono,
            'id_credito': p.id_credito,
            'fuente': 'status7',
            'coordenadas': coord_str,
        })

        geom_list.append(geom)
        id_poligon_list.append(p.id_poligono)
        id_credito_list.append(p.id_credito)
        fuente_list.append('status7')

        count_status7 += 1

    # ------------------------------------------------------------------
    # d) FUENTE nuevo_dic: ValidacionDiciembre.estatus_validacion='NUEVO'
    #    unida a CapaDiciembre para obtener las coordenadas
    # ------------------------------------------------------------------
    nuevos = (
        db.session.query(ValidacionDiciembre, CapaDiciembre)
        .join(CapaDiciembre, ValidacionDiciembre.capa_diciembre_id == CapaDiciembre.id)
        .filter(ValidacionDiciembre.estatus_validacion == 'NUEVO')
        .all()
    )

    count_nuevo_dic = 0
    skip_nuevo_dic = 0
    for vd, cd in nuevos:
        coord_str = cd.coordenadas
        geom = _parse_coords_to_polygon(coord_str)
        if geom is None:
            skip_nuevo_dic += 1
            continue

        rows.append({
            'id_poligono_unico': vd.id_poligono,
            'id_credito': vd.id_credito,
            'fuente': 'nuevo_dic',
            'coordenadas': coord_str,
        })

        geom_list.append(geom)
        id_poligon_list.append(vd.id_poligono)
        id_credito_list.append(vd.id_credito)
        fuente_list.append('nuevo_dic')

        count_nuevo_dic += 1

    # ------------------------------------------------------------------
    # e) INSERT masivo en mega_capa_v3
    # ------------------------------------------------------------------
    if rows:
        db.session.bulk_insert_mappings(MegaCapaV3, rows)
        db.session.commit()

    # ------------------------------------------------------------------
    # f) GENERAR SHAPEFILE data/MEGA_CAPA_V3.shp
    #    Columnas: ID_POLIGON, ID_CREDITO, FUENTE, geometry (max 10 chars)
    # ------------------------------------------------------------------
    gdf_out = gpd.GeoDataFrame(
        {
            'ID_POLIGON': id_poligon_list,
            'ID_CREDITO': id_credito_list,
            'FUENTE': fuente_list,
            'geometry': geom_list,
        },
        crs='EPSG:4326',
    )
    gdf_out.to_file('data/MEGA_CAPA_V3.shp')

    # ------------------------------------------------------------------
    # g) Recargar cache en caliente (solo util despues del swap V2->V3)
    # ------------------------------------------------------------------
    shp_cache.reload_mega()

    # ------------------------------------------------------------------
    # h) Resultado
    # ------------------------------------------------------------------
    total = count_v2 + count_status7 + count_nuevo_dic
    result = {
        'v2': count_v2,
        'status7': count_status7,
        'nuevo_dic': count_nuevo_dic,
        'total': total,
        'status7_skipped': skip_status7,
        'nuevo_dic_skipped': skip_nuevo_dic,
    }
    print(result)
    return result
