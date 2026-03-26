from extensions import db
from datetime import datetime
from sqlalchemy import Column, Integer, Text, Float, Boolean, DateTime


class BackupAnalizador15K(db.Model):
    __tablename__ = "backup_analizador_15k"

    id = Column(Integer, primary_key=True)
    backup_id = Column(Text, nullable=False, index=True)  # UUID or timestamp string identifying this backup run
    backup_fecha = Column(DateTime, default=datetime.utcnow)

    # Mirror ALL columns from Analizador15K:
    idx_shp = Column(Integer, nullable=False)
    id_poligon = Column(Text)
    id_credito = Column(Text)
    nombre_zip = Column(Text)
    estatus_chapingo = Column(Text)
    id_poligono_unico = Column(Text)
    superficie_chapingo = Column(Float)
    comentario_chapingo = Column(Text)
    superficie_calculada = Column(Float)
    tiene_decision = Column(Boolean, default=False)
    region = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'backup_fecha': self.backup_fecha.isoformat() if self.backup_fecha else None,
            'idx_shp': self.idx_shp,
            'id_poligon': self.id_poligon,
            'id_credito': self.id_credito,
            'nombre_zip': self.nombre_zip,
            'estatus_chapingo': self.estatus_chapingo,
            'id_poligono_unico': self.id_poligono_unico,
            'superficie_chapingo': self.superficie_chapingo,
            'comentario_chapingo': self.comentario_chapingo,
            'superficie_calculada': self.superficie_calculada,
            'tiene_decision': self.tiene_decision,
            'region': self.region,
        }
