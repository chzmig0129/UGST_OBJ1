"""
convertir_base_fo_a_shp.py

Reads Base_FO_CON_06_CONSERVADOS.xlsx from the project root and converts it to
a shapefile at data/CAPA_DICIEMBRE_VALIDADOS.shp with the 5 attribute columns:
    ID_POLIGONO, IF, ID_CREDITO, ID_PERSONA, SUPERFICIE

Geometry is built via utils.validacion_megacapa.construir_geometria, which
handles the 'lat,lon | lat,lon | ...' coordinate format, polygon ordering,
ring closing, and buffer(0) for self-intersecting polygons.

CRS is set to EPSG:4326.

Usage (from project root):
    python scripts/convertir_base_fo_a_shp.py
    # or:
    .venv/bin/python scripts/convertir_base_fo_a_shp.py
"""

import os
import sys

# Ensure the project root is on sys.path so utils.* imports work regardless of
# how/where the script is invoked.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping

from utils.validacion_megacapa import construir_geometria

XLSX_PATH = os.path.join(PROJECT_ROOT, "Base_FO_CON_06_CONSERVADOS.xlsx")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "CAPA_DICIEMBRE_VALIDADOS.shp")
SHEET = "Sheet1"
ATTR_COLS = ["ID_POLIGONO", "IF", "ID_CREDITO", "ID_PERSONA", "SUPERFICIE"]
CRS = "EPSG:4326"


def main():
    # ---- 1. Read xlsx --------------------------------------------------
    print(f"Leyendo: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, sheet_name=SHEET)
    filas_leidas = len(df)
    print(f"Filas leidas: {filas_leidas}")

    # ---- 2. Build geometries -------------------------------------------
    geometrias = []
    indices_validos = []
    descartadas = 0

    for i, row in df.iterrows():
        coordenadas = str(row["COORDENADAS"]) if pd.notna(row["COORDENADAS"]) else ""
        geom, error = construir_geometria(coordenadas)
        if geom is None:
            descartadas += 1
            print(f"  [DESCARTADA] fila {i} ID_POLIGONO={row['ID_POLIGONO']!r}: {error}")
        else:
            geometrias.append(geom)
            indices_validos.append(i)

    # ---- 3. Build GeoDataFrame -----------------------------------------
    df_valido = df.loc[indices_validos, ATTR_COLS].reset_index(drop=True)
    gdf = gpd.GeoDataFrame(df_valido, geometry=geometrias, crs=CRS)

    # ---- 4. Write shapefile --------------------------------------------
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    gdf.to_file(OUTPUT_PATH)

    # ---- 5. Summary -----------------------------------------------------
    filas_escritas = len(gdf)
    print()
    print("=" * 50)
    print(f"Filas leidas    : {filas_leidas}")
    print(f"Filas escritas  : {filas_escritas}")
    print(f"Filas descartadas: {descartadas}")
    print(f"CRS             : {gdf.crs}")
    print(f"Columnas        : {list(gdf.columns)}")
    print(f"Salida          : {OUTPUT_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()
