from datetime import datetime
from utils.database import db


class ValidacionMegacapa(db.Model):
    """Resultado de validación de cada polígono cargado contra la megacapa."""
    __tablename__ = 'validacion_megacapa'

    id = db.Column(db.Integer, primary_key=True)
    poligono_id = db.Column(db.Integer, nullable=False)  # References poligono.id (no FK constraint to avoid import order issues)
    id_poligono = db.Column(db.Text, nullable=True)       # ID_POLIGONO del polígono cargado
    id_credito = db.Column(db.Text, nullable=True)         # ID_CREDITO del polígono cargado
    estatus_megacapa = db.Column(db.Text, nullable=False)  # 'VINCULAR' o 'NUEVO'
    id_poligono_unico = db.Column(db.Text, nullable=True)  # ID_POLIGON de la megacapa (solo VINCULAR)
    porcentaje_traslape = db.Column(db.Float, nullable=True)  # % de traslape (0-100)
    id_credito_megacapa = db.Column(db.Text, nullable=True)   # ID_CREDITO de la megacapa match
    motivo = db.Column(db.Text, nullable=True)             # Razón: 'traslape>=85%', 'traslape<85%', 'sin_coordenadas', 'puntos_insuficientes'
    fecha_validacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Note: no ORM relationship — Poligono is defined in app.py, use poligono_id for joins

    def to_dict(self):
        return {
            'id': self.id,
            'poligono_id': self.poligono_id,
            'id_poligono': self.id_poligono,
            'id_credito': self.id_credito,
            'estatus_megacapa': self.estatus_megacapa,
            'id_poligono_unico': self.id_poligono_unico,
            'porcentaje_traslape': self.porcentaje_traslape,
            'id_credito_megacapa': self.id_credito_megacapa,
            'motivo': self.motivo,
            'fecha_validacion': self.fecha_validacion.isoformat() if self.fecha_validacion else None,
        }
