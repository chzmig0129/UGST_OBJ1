from datetime import datetime
from extensions import db

class ValidacionDiciembre(db.Model):
    '''Resultado de validación de cada polígono de Capa Diciembre contra (megacapa + estatus 7).'''
    __tablename__ = 'validacion_diciembre'

    id = db.Column(db.Integer, primary_key=True)
    capa_diciembre_id = db.Column(db.Integer, nullable=False)  # FK lógica a capa_diciembre.id
    id_poligono = db.Column(db.Text, nullable=True)   # ID_POLIGONO del polígono de Diciembre (copia para facilitar queries)
    id_credito = db.Column(db.Text, nullable=True)    # ID_CREDITO del polígono de Diciembre
    estatus_validacion = db.Column(db.Text, nullable=False)  # 'VINCULAR' | 'NUEVO'
    estatus_manual = db.Column(db.Boolean, default=False)    # True si el usuario cambió el estatus manualmente
    id_poligono_match = db.Column(db.Text, nullable=True)    # ID_POLIGONO del match (o 'SIN ID' o 'SIN NINGÚN ID')
    id_credito_match = db.Column(db.Text, nullable=True)     # ID_CREDITO del match
    porcentaje_traslape = db.Column(db.Float, nullable=True)
    fuente_match = db.Column(db.Text, nullable=True)  # 'megacapa' | 'estatus7' | NULL (si NUEVO sin traslape)
    motivo = db.Column(db.Text, nullable=True)        # 'traslape>=85%' | 'traslape<85%' | 'sin_traslape' | 'sin_coordenadas' | etc
    fecha_validacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'capa_diciembre_id': self.capa_diciembre_id,
            'id_poligono': self.id_poligono,
            'id_credito': self.id_credito,
            'estatus_validacion': self.estatus_validacion,
            'estatus_manual': self.estatus_manual,
            'id_poligono_match': self.id_poligono_match,
            'id_credito_match': self.id_credito_match,
            'porcentaje_traslape': self.porcentaje_traslape,
            'fuente_match': self.fuente_match,
            'motivo': self.motivo,
            'fecha_validacion': self.fecha_validacion.isoformat() if self.fecha_validacion else None,
        }
