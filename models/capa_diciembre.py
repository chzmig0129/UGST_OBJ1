from datetime import datetime
from extensions import db

class CapaDiciembre(db.Model):
    __tablename__ = 'capa_diciembre'

    id = db.Column(db.Integer, primary_key=True)
    id_poligono = db.Column(db.Text, nullable=True)
    if_val = db.Column(db.Text, nullable=True)
    id_credito = db.Column(db.Text, nullable=True)
    id_persona = db.Column(db.Text, nullable=True)
    superficie = db.Column(db.Float, nullable=True)
    coordenadas = db.Column(db.Text, nullable=False)  # formato 'lat,lon | lat,lon | ...'
    fecha_carga = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'id_poligono': self.id_poligono,
            'if_val': self.if_val,
            'id_credito': self.id_credito,
            'id_persona': self.id_persona,
            'superficie': self.superficie,
            'coordenadas': self.coordenadas,
            'fecha_carga': self.fecha_carga.isoformat() if self.fecha_carga else None,
        }
