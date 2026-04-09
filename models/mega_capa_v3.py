from datetime import datetime
from extensions import db

class MegaCapaV3(db.Model):
    '''Union de MEGA_CAPA_V2 + Poligono.estatus=7 + ValidacionDiciembre.NUEVO.'''
    __tablename__ = 'mega_capa_v3'

    id = db.Column(db.Integer, primary_key=True)
    id_poligono_unico = db.Column(db.Text, nullable=True)   # ID del poligono (ID_POLIGON o id_poligono)
    id_credito = db.Column(db.Text, nullable=True)
    fuente = db.Column(db.Text, nullable=False)             # 'v2' | 'status7' | 'nuevo_dic'
    coordenadas = db.Column(db.Text, nullable=False)        # 'lat,lon | lat,lon | ...' (mismo formato que Poligono.coordenadas_corregidas)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'id_poligono_unico': self.id_poligono_unico,
            'id_credito': self.id_credito,
            'fuente': self.fuente,
            'coordenadas': self.coordenadas,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }
