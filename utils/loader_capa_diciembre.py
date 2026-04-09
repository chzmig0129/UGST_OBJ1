def cargar_capa_diciembre_desde_shape(
    shapefile_path='data/CAPA_DICIEMBRE_VALIDADOS.shp',
    truncate=True,
):
    """
    Lee el shapefile CAPA_DICIEMBRE_VALIDADOS.shp y puebla la tabla capa_diciembre.
    Si truncate=True, vacía la tabla antes de insertar (re-carga limpia).
    Retorna dict con {'insertados': N, 'descartados': M, 'errores': [...]}.
    """
    import geopandas as gpd
    from extensions import db
    from models.capa_diciembre import CapaDiciembre

    gdf = gpd.read_file(shapefile_path)
    if truncate:
        db.session.query(CapaDiciembre).delete()
        db.session.commit()

    insertados = 0
    descartados = 0
    errores = []

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            descartados += 1
            continue
        # Reconstruir string 'lat,lon | lat,lon | ...' desde la geometría para guardarlo
        try:
            coords_list = list(geom.exterior.coords)  # [(lon,lat), ...]
            coords_str = ' | '.join(f'{lat},{lon}' for lon, lat in coords_list)
        except Exception as e:
            errores.append(str(e))
            descartados += 1
            continue

        def _clean(v):
            if v is None:
                return None
            s = str(v).strip()
            return s if s and s != 'nan' else None

        registro = CapaDiciembre(
            id_poligono=_clean(row.get('ID_POLIGON') or row.get('ID_POLIGONO')),
            if_val=_clean(row.get('IF')),
            id_credito=_clean(row.get('ID_CREDITO')),
            id_persona=_clean(row.get('ID_PERSONA')),
            superficie=float(row['SUPERFICIE']) if row.get('SUPERFICIE') not in (None, '') else None,
            coordenadas=coords_str,
        )
        db.session.add(registro)
        insertados += 1

    db.session.commit()
    return {'insertados': insertados, 'descartados': descartados, 'errores': errores}
