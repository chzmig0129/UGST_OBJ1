"""
Load all validation 15K shapefile records into the analizador_15k PostgreSQL table.

Usage:
    python scripts/load_15k.py

Can be run multiple times safely — uses INSERT ON CONFLICT DO NOTHING on idx_shp.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models.analizador_15k import Analizador15K
from utils.shapefile_cache import shp_cache
import numpy as np


def calcular_region(lat):
    """Divide Mexico into 3 regions by latitude terciles."""
    if lat is None:
        return None
    if lat < 22.75:
        return 'sur'
    elif lat < 23.02:
        return 'centro'
    else:
        return 'norte'


def main():
    with app.app_context():
        # Create table if not exists
        db.create_all()
        
        # Check if already loaded
        existing = Analizador15K.query.count()
        if existing > 0:
            print(f"[load_15k] Table already has {existing} records.")
            resp = input("Do you want to reload? This will skip existing records. (y/N): ")
            if resp.lower() != 'y':
                print("[load_15k] Aborted.")
                return
        
        # Load shapefile
        v = shp_cache.validacion
        if v is None:
            print("[load_15k] ERROR: Could not load validation shapefile.")
            return
        
        print(f"[load_15k] Loading {len(v)} records from validation shapefile...")
        
        batch_size = 500
        loaded = 0
        skipped = 0
        
        for i in range(len(v)):
            row = v.iloc[i]
            
            # Check if already exists
            if Analizador15K.query.filter_by(idx_shp=i).first():
                skipped += 1
                continue
            
            # Calculate centroid
            centroid = row.geometry.centroid
            lat = round(centroid.y, 6)
            lon = round(centroid.x, 6)
            
            record = Analizador15K(
                idx_shp=i,
                id_poligon=str(row.get('ID_POLIGON', '')) if 'ID_POLIGON' in row.index else None,
                id_credito=str(row.get('ID_CREDITO', '')) if 'ID_CREDITO' in row.index else None,
                nombre_zip=str(row.get('NOMBRE_ZIP', '')) if 'NOMBRE_ZIP' in row.index else None,
                estatus_shp=str(row.get('Estatus', '')) if 'Estatus' in row.index and row.get('Estatus') else None,
                id_unico=str(row.get('ID_Unico', '')) if 'ID_Unico' in row.index and row.get('ID_Unico') else None,
                superficie_shp=float(row.get('Superficie', 0)) if 'Superficie' in row.index else 0.0,
                centroid_lat=lat,
                centroid_lon=lon,
                region=calcular_region(lat),
            )
            db.session.add(record)
            loaded += 1
            
            if loaded % batch_size == 0:
                db.session.commit()
                print(f"  ... {loaded} records loaded")
        
        db.session.commit()
        print(f"[load_15k] Done! Loaded: {loaded}, Skipped: {skipped}")
        
        # Show region distribution
        for region in ['norte', 'centro', 'sur']:
            count = Analizador15K.query.filter_by(region=region).count()
            print(f"  Region {region}: {count} polígonos")


if __name__ == '__main__':
    main()
