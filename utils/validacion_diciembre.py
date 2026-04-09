'''
Motor de validación Capa Diciembre vs (MEGA_CAPA_V2 + polígonos estatus=7 no excluidos).
'''
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon as ShapelyPolygon
from utils.shapefile_cache import shp_cache
from utils.validacion_megacapa import construir_geometria


def _build_universo_combinado():
    '''
    Construye el GeoDataFrame unificado (megacapa + estatus 7) sobre el cual se valida Capa Diciembre.
    Retorna un GeoDataFrame con columnas: geometry, fuente ('megacapa'|'estatus7'), id_poligono_match, id_credito_match.
    '''
    from extensions import db
    from models.validacion_megacapa import ValidacionMegacapa
    from models.segunda_validacion_poligono import SegundaValidacionPoligono

    # 1) Megacapa
    mega = shp_cache.mega.copy()
    mega['fuente'] = 'megacapa'
    mega['id_poligono_match'] = mega['ID_POLIGON'].astype(str)
    mega['id_credito_match'] = mega['ID_CREDITO'].astype(str)
    mega_gdf = mega[['geometry', 'fuente', 'id_poligono_match', 'id_credito_match']].copy()

    # 2) Polígonos estatus=7 no excluidos (importar Poligono dentro de la función para evitar import circular)
    from app import Poligono  # Poligono vive en app.py
    vincular_ids = set(v.poligono_id for v in ValidacionMegacapa.query.filter_by(estatus_megacapa='VINCULAR').all())
    excluir_sv = set(sv.poligono_id for sv in SegundaValidacionPoligono.query.filter(SegundaValidacionPoligono.decision.in_(['ELIMINAR', 'VINCULAR'])).all())
    excluir = vincular_ids | excluir_sv

    query = Poligono.query.filter(Poligono.estatus == '7')
    if excluir:
        query = query.filter(~Poligono.id.in_(excluir))
    poligonos_7 = query.all()

    rows = []
    for p in poligonos_7:
        geom, err = construir_geometria(p.coordenadas_corregidas)
        if geom is None or geom.is_empty:
            continue
        # Fallbacks para IDs vacíos
        idp = (p.id_poligono or '').strip()
        idc = (p.id_credito or '').strip()
        if not idp and not idc:
            id_poligono_match = 'SIN NINGUN ID'
            id_credito_match = None
        elif not idp and idc:
            id_poligono_match = 'SIN ID'
            id_credito_match = idc
        else:
            id_poligono_match = idp
            id_credito_match = idc or None
        rows.append({
            'geometry': geom,
            'fuente': 'estatus7',
            'id_poligono_match': id_poligono_match,
            'id_credito_match': id_credito_match,
        })

    if rows:
        estatus7_gdf = gpd.GeoDataFrame(rows, crs='EPSG:4326')
        universo = pd.concat([mega_gdf, estatus7_gdf], ignore_index=True)
        universo = gpd.GeoDataFrame(universo, crs='EPSG:4326')
    else:
        universo = mega_gdf

    return universo


def ejecutar_validacion_diciembre(umbral_traslape=85.0):
    '''
    Ejecuta la validación de la Capa Diciembre.
    - Vacía la tabla validacion_diciembre
    - Para cada CapaDiciembre construye geometría
    - Busca mejor match en el universo combinado
    - Clasifica VINCULAR (>=umbral) / NUEVO (<umbral)
    - Persiste en ValidacionDiciembre
    Retorna dict con contadores {'total', 'vinculados', 'nuevos', 'errores'}.
    '''
    from extensions import db
    from models.capa_diciembre import CapaDiciembre
    from models.validacion_diciembre import ValidacionDiciembre

    # Vaciar resultados previos
    db.session.query(ValidacionDiciembre).delete()
    db.session.commit()

    universo = _build_universo_combinado()
    sindex = universo.sindex

    total = 0
    vinculados = 0
    nuevos = 0
    errores = 0

    for cd in CapaDiciembre.query.all():
        total += 1
        geom, err = construir_geometria(cd.coordenadas)
        if geom is None or geom.is_empty:
            errores += 1
            reg = ValidacionDiciembre(
                capa_diciembre_id=cd.id,
                id_poligono=cd.id_poligono,
                id_credito=cd.id_credito,
                estatus_validacion='NUEVO',
                motivo=err or 'geometria_invalida',
            )
            db.session.add(reg)
            continue

        candidates = list(sindex.intersection(geom.bounds))
        best = 0.0
        best_row = None
        for idx in candidates:
            other = universo.iloc[idx]
            og = other.geometry
            if og is None or og.is_empty:
                continue
            try:
                if not geom.intersects(og):
                    continue
                inter = geom.intersection(og).area
                overlap = (inter / geom.area * 100) if geom.area > 0 else 0.0
                if overlap > best:
                    best = overlap
                    best_row = other
            except Exception:
                continue

        if best >= umbral_traslape:
            vinculados += 1
            reg = ValidacionDiciembre(
                capa_diciembre_id=cd.id,
                id_poligono=cd.id_poligono,
                id_credito=cd.id_credito,
                estatus_validacion='VINCULAR',
                id_poligono_match=best_row['id_poligono_match'],
                id_credito_match=best_row['id_credito_match'],
                porcentaje_traslape=round(best, 2),
                fuente_match=best_row['fuente'],
                motivo=f'traslape>={umbral_traslape}%',
            )
        else:
            nuevos += 1
            reg = ValidacionDiciembre(
                capa_diciembre_id=cd.id,
                id_poligono=cd.id_poligono,
                id_credito=cd.id_credito,
                estatus_validacion='NUEVO',
                id_poligono_match=best_row['id_poligono_match'] if best_row is not None else None,
                id_credito_match=best_row['id_credito_match'] if best_row is not None else None,
                porcentaje_traslape=round(best, 2) if best > 0 else None,
                fuente_match=best_row['fuente'] if best_row is not None else None,
                motivo=f'traslape<{umbral_traslape}%' if best > 0 else 'sin_traslape',
            )
        db.session.add(reg)

        # Commit parcial cada 500 para no saturar
        if total % 500 == 0:
            db.session.commit()

    db.session.commit()
    return {'total': total, 'vinculados': vinculados, 'nuevos': nuevos, 'errores': errores}
