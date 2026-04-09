#!/usr/bin/env python3
"""CLI: genera Mega Capa V3 (shapefile + tabla). Uso: docker compose exec web python scripts/build_mega_capa_v3.py"""
import sys
import os

# Asegurar que la raiz del proyecto este en el path para que app.py se importe correctamente.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from utils.build_mega_capa_v3 import build_mega_capa_v3

if __name__ == '__main__':
    with app.app_context():
        result = build_mega_capa_v3()
        print('OK:', result)
        sys.exit(0)
