"""
Lazy-loading cache for large shapefiles.

Shapefiles are only read from disk the first time each property is accessed.
Call shp_cache.preload_all() at startup (e.g. with gunicorn preload_app=True)
to force-load everything up front and avoid first-request latency.
"""

import geopandas as gpd


class ShapefileCache:
    def __init__(self):
        self._municipios = None
        self._validacion = None
        self._mega = None

    # ------------------------------------------------------------------
    # Public lazy properties
    # ------------------------------------------------------------------

    @property
    def municipios(self):
        if self._municipios is None:
            self._municipios = self._load_municipios()
        return self._municipios

    @property
    def validacion(self):
        if self._validacion is None:
            self._validacion = self._load_validacion()
        return self._validacion

    @property
    def mega(self):
        if self._mega is None:
            self._mega = self._load_mega()
        return self._mega

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_municipios(self):
        gdf = gpd.read_file('data/mun22gw.shp')
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        gdf = gdf[['NOMGEO', 'NOM_ENT', 'geometry']]
        print("ShapefileCache: municipios cargado. Columnas:", gdf.columns.tolist())
        return gdf

    def _load_validacion(self):
        gdf = gpd.read_file('data/VALIDACION_UNIFICADO.shp')
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        print("ShapefileCache: validacion cargado. Columnas:", gdf.columns.tolist())
        return gdf

    def _load_mega(self):
        gdf = gpd.read_file('data/MEGA_CAPA_V1_OL.shp')
        if gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        print("ShapefileCache: mega cargado. Columnas:", gdf.columns.tolist())
        return gdf

    # ------------------------------------------------------------------
    # Preload helper
    # ------------------------------------------------------------------

    def preload_all(self):
        """Force-load all shapefiles. Call at startup for gunicorn preload_app."""
        _ = self.municipios
        _ = self.validacion
        _ = self.mega


# Module-level singleton — import this everywhere
shp_cache = ShapefileCache()
