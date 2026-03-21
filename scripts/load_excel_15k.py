"""
Load Excel data from HISTORICO POLIGONOS 15K into the analizador_15k table.
Matches records by ID_POLIGONO column.

Usage: python scripts/load_excel_15k.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models.analizador_15k import Analizador15K
import openpyxl
from datetime import datetime

EXCEL_PATH = 'HISTORICO POLIGONOS 15K/0. Poligonos y solicitudes faltantes para validacion de traslapes y duplicados .xlsx'

def main():
    with app.app_context():
        wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
        ws = wb['POLIGONOS']

        rows = list(ws.iter_rows(min_row=2, values_only=True))  # skip header
        print(f'[load_excel] {len(rows)} rows in Excel')

        updated = 0
        not_found = 0

        for row in rows:
            id_poligono = str(row[13]).strip() if row[13] else None
            if not id_poligono:
                continue

            # Find matching record by id_poligon
            record = Analizador15K.query.filter_by(id_poligon=id_poligono).first()
            if not record:
                not_found += 1
                continue

            # Update Excel columns
            record.intermediario_financiero = str(row[0]).strip() if row[0] else None
            record.id_dtu = str(row[2]).strip() if row[2] else None
            record.nombre_intermediario = str(row[3]).strip() if row[3] else None
            record.fecha_creacion_credito = row[4] if isinstance(row[4], datetime) else None
            record.fecha_autorizacion = row[5] if isinstance(row[5], datetime) else None
            record.fecha_vencimiento = row[6] if isinstance(row[6], datetime) else None
            record.accion = int(row[7]) if row[7] else None
            record.descripcion_accion = str(row[8]).strip() if row[8] else None
            record.id_persona = str(row[9]).strip() if row[9] else None
            record.estado = str(row[10]).strip() if row[10] else None
            record.municipio = str(row[11]).strip() if row[11] else None
            record.id_carga = str(row[12]).strip() if row[12] else None
            record.superficie_excel = float(row[15]) if row[15] else None
            record.descripcion = str(row[16]).strip() if row[16] else None
            record.estatus_excel = str(row[17]).strip() if row[17] else None
            record.estado_credito = str(row[18]).strip() if row[18] else None
            record.cadena = str(row[19]).strip() if row[19] else None
            record.comentarios_excel = str(row[20]).strip() if row[20] else None

            # Also update id_credito from Excel if not set
            if row[1] and not record.id_credito:
                record.id_credito = str(row[1]).strip()

            updated += 1

            if updated % 500 == 0:
                db.session.commit()
                print(f'  ... {updated} updated')

        db.session.commit()
        print(f'[load_excel] Done! Updated: {updated}, Not found: {not_found}')

if __name__ == '__main__':
    main()
