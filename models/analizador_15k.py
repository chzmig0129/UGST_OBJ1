from extensions import db
from datetime import datetime


class Analizador15K(db.Model):
    __tablename__ = 'analizador_15k'

    id = db.Column(db.Integer, primary_key=True)
    idx_shp = db.Column(db.Integer, unique=True, nullable=False, index=True)
    
    # Data from shapefile (loaded once)
    id_poligon = db.Column(db.Text)
    id_credito = db.Column(db.Text)
    nombre_zip = db.Column(db.Text)
    estatus_shp = db.Column(db.Text)  # original status from SHP
    id_unico = db.Column(db.Text)
    superficie_shp = db.Column(db.Float, default=0.0)
    centroid_lat = db.Column(db.Float)
    centroid_lon = db.Column(db.Float)
    
    # Region assignment (auto-calculated from centroid)
    region = db.Column(db.Text, index=True)  # 'norte', 'centro', 'sur'
    
    # User assignment
    usuario_asignado_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    usuario_asignado = db.relationship('User', foreign_keys=[usuario_asignado_id], backref='poligonos_asignados')
    
    # Work fields (filled by user)
    estatus_chapingo = db.Column(db.Text)  # VINCULAR, NUEVO, ELIMINAR
    id_poligono_unico = db.Column(db.Text)
    superficie_chapingo = db.Column(db.Float)
    comentario_chapingo = db.Column(db.Text)
    superficie_calculada = db.Column(db.Float)
    tiene_decision = db.Column(db.Boolean, default=False, index=True)
    
    # Audit
    decidido_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    decidido_por = db.relationship('User', foreign_keys=[decidido_por_id])
    fecha_decision = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'idx_shp': self.idx_shp,
            'id_poligon': self.id_poligon,
            'id_credito': self.id_credito,
            'nombre_zip': self.nombre_zip,
            'estatus_shp': self.estatus_shp,
            'id_unico': self.id_unico,
            'superficie_shp': self.superficie_shp,
            'centroid_lat': self.centroid_lat,
            'centroid_lon': self.centroid_lon,
            'region': self.region,
            'usuario_asignado_id': self.usuario_asignado_id,
            'estatus_chapingo': self.estatus_chapingo,
            'id_poligono_unico': self.id_poligono_unico,
            'superficie_chapingo': self.superficie_chapingo,
            'comentario_chapingo': self.comentario_chapingo,
            'superficie_calculada': self.superficie_calculada,
            'tiene_decision': self.tiene_decision,
            'decidido_por_id': self.decidido_por_id,
            'fecha_decision': self.fecha_decision.isoformat() if self.fecha_decision else None,
        }
