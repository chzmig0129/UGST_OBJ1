from datetime import datetime
from extensions import db


class SegundaValidacionPoligono(db.Model):
    """Results of segunda validacion (NUEVO vs NUEVO overlap) for Validacion de Poligonos."""
    __tablename__ = 'segunda_validacion_poligono'

    id = db.Column(db.Integer, primary_key=True)
    poligono_id = db.Column(db.Integer, nullable=False, index=True)  # References Poligono.id
    id_poligono = db.Column(db.Text)        # Poligono.id_poligono
    id_credito = db.Column(db.Text)         # Poligono.id_credito

    # Group assignment
    group_id = db.Column(db.Integer, index=True)  # Group number (1, 2, 3...)
    is_principal = db.Column(db.Boolean, default=False)

    # Decision
    decision = db.Column(db.Text)           # 'NUEVO' | 'VINCULAR' | 'ELIMINAR'
    principal_poligono_id = db.Column(db.Integer)  # poligono_id of the principal in the group
    principal_id_poligono = db.Column(db.Text)     # id_poligono of the principal
    razon = db.Column(db.Text)              # Human-readable reason

    # Overlap info
    max_overlap_pct = db.Column(db.Float)   # Max overlap percentage with another NUEVO

    fecha_validacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'poligono_id': self.poligono_id,
            'id_poligono': self.id_poligono,
            'id_credito': self.id_credito,
            'group_id': self.group_id,
            'is_principal': self.is_principal,
            'decision': self.decision,
            'principal_poligono_id': self.principal_poligono_id,
            'principal_id_poligono': self.principal_id_poligono,
            'razon': self.razon,
            'max_overlap_pct': self.max_overlap_pct,
            'fecha_validacion': self.fecha_validacion.isoformat() if self.fecha_validacion else None,
        }
