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

    # Excel data columns (from HISTORICO POLIGONOS 15K)
    intermediario_financiero = db.Column(db.Text)   # "IF"
    id_dtu = db.Column(db.Text)                      # "ID DTU"
    nombre_intermediario = db.Column(db.Text)         # "NOMBRE_INTERMEDIARIO_1"
    fecha_creacion_credito = db.Column(db.DateTime)  # "FECHA CREACIÓN"
    fecha_autorizacion = db.Column(db.DateTime)      # "FECHA AUTORIZACION"
    fecha_vencimiento = db.Column(db.DateTime)       # "FECHA VENCIMIENTO"
    accion = db.Column(db.Integer)                   # "ACCION"
    descripcion_accion = db.Column(db.Text)          # "DESCRIPCION ACCION"
    id_persona = db.Column(db.Text)                  # "ID PERSONA"
    estado = db.Column(db.Text)                      # "ESTADO"
    municipio = db.Column(db.Text)                   # "MUNICIPIO"
    id_carga = db.Column(db.Text)                    # "ID_CARGA"
    superficie_excel = db.Column(db.Float)           # "SUPERFICIE"
    descripcion = db.Column(db.Text)                 # "DESCRIPCION"
    estatus_excel = db.Column(db.Text)               # "ESTATUS"
    estado_credito = db.Column(db.Text)              # "ESTADO_CREDITO"
    cadena = db.Column(db.Text)                      # "CADENA"
    comentarios_excel = db.Column(db.Text)           # "COMENTARIOS"

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
            # Excel data columns
            'intermediario_financiero': self.intermediario_financiero,
            'id_dtu': self.id_dtu,
            'nombre_intermediario': self.nombre_intermediario,
            'fecha_creacion_credito': self.fecha_creacion_credito.isoformat() if self.fecha_creacion_credito else None,
            'fecha_autorizacion': self.fecha_autorizacion.isoformat() if self.fecha_autorizacion else None,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'accion': self.accion,
            'descripcion_accion': self.descripcion_accion,
            'id_persona': self.id_persona,
            'estado': self.estado,
            'municipio': self.municipio,
            'id_carga': self.id_carga,
            'superficie_excel': self.superficie_excel,
            'descripcion': self.descripcion,
            'estatus_excel': self.estatus_excel,
            'estado_credito': self.estado_credito,
            'cadena': self.cadena,
            'comentarios_excel': self.comentarios_excel,
            # Region and assignment
            'region': self.region,
            'usuario_asignado_id': self.usuario_asignado_id,
            # Work fields
            'estatus_chapingo': self.estatus_chapingo,
            'id_poligono_unico': self.id_poligono_unico,
            'superficie_chapingo': self.superficie_chapingo,
            'comentario_chapingo': self.comentario_chapingo,
            'superficie_calculada': self.superficie_calculada,
            'tiene_decision': self.tiene_decision,
            'decidido_por_id': self.decidido_por_id,
            'fecha_decision': self.fecha_decision.isoformat() if self.fecha_decision else None,
        }
