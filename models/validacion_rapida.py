from datetime import datetime
from utils.database import db

class RegistroValidacionRapida(db.Model):
    """
    Modelo de datos para la validación rápida que almacena registros del Excel cargado
    y añade campos adicionales para el proceso de validación.
    """
    __tablename__ = 'registros_validacion_rapida'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos provenientes del Excel
    if_val = db.Column(db.String(100))
    id_credito = db.Column(db.String(100))
    estatus_credito = db.Column(db.String(50), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_autorizacion = db.Column(db.Date, nullable=True)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    accion = db.Column(db.String(100), nullable=True)
    id_persona = db.Column(db.String(50), nullable=True)
    id_carga = db.Column(db.String(50), nullable=True)
    id_poligono = db.Column(db.String(100))
    superficie = db.Column(db.Float)
    coordenadas = db.Column(db.Text, nullable=True)
    estatus = db.Column(db.String(50))
    
    # Campos adicionales para validación
    nuevo_estatus = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    traslape = db.Column(db.String(50))
    fo_con_xx = db.Column(db.String(50))
    
    # Metadata
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Datos adicionales (se almacenarán como JSON)
    datos_extra = db.Column(db.Text)
    
    def __repr__(self):
        return f'<RegistroValidacionRapida {self.id_poligono}>'
        
    def to_dict(self):
        """Convierte el objeto a un diccionario para su fácil serialización"""
        return {
            'db_id': self.id,
            'IF': self.if_val,
            'ID_CREDITO': self.id_credito,
            'ESTATUS_CREDITO': self.estatus_credito,
            'FECHA_CREACION': self.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_creacion else None,
            'FECHA_AUTORIZACION': self.fecha_autorizacion.strftime('%Y-%m-%d') if self.fecha_autorizacion else None,
            'FECHA_VENCIMIENTO': self.fecha_vencimiento.strftime('%Y-%m-%d') if self.fecha_vencimiento else None,
            'ACCION': self.accion,
            'ID_PERSONA': self.id_persona,
            'ID_CARGA': self.id_carga,
            'ID_POLIGONO': self.id_poligono,
            'SUPERFICIE': self.superficie,
            'COORDENADAS': self.coordenadas,
            'ESTATUS': self.estatus,
            'NUEVO_ESTATUS': self.nuevo_estatus,
            'DESCRIPCION': self.descripcion,
            'TRASLAPE': self.traslape,
            'FO_CON_XX': self.fo_con_xx,
            'fecha_creacion': self.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_creacion else None,
            'fecha_modificacion': self.fecha_modificacion.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_modificacion else None
        }

    @staticmethod
    def from_dict(data):
        """Crea un objeto a partir de un diccionario"""
        registro = RegistroValidacionRapida()
        
        registro.if_val = data.get('IF')
        registro.id_credito = data.get('ID_CREDITO') 
        registro.estatus_credito = data.get('ESTATUS_CREDITO')
        
        # Manejo de fechas (convertir de str a Date)
        if data.get('FECHA_CREACION'):
            try:
                if isinstance(data['FECHA_CREACION'], str):
                    registro.fecha_creacion = datetime.strptime(data['FECHA_CREACION'], '%Y-%m-%d').date()
                else:
                    registro.fecha_creacion = data['FECHA_CREACION']
            except (ValueError, TypeError):
                registro.fecha_creacion = None
        
        if data.get('FECHA_AUTORIZACION'):
            try:
                if isinstance(data['FECHA_AUTORIZACION'], str):
                    registro.fecha_autorizacion = datetime.strptime(data['FECHA_AUTORIZACION'], '%Y-%m-%d').date()
                else:
                    registro.fecha_autorizacion = data['FECHA_AUTORIZACION']
            except (ValueError, TypeError):
                registro.fecha_autorizacion = None
                
        if data.get('FECHA_VENCIMIENTO'):
            try:
                if isinstance(data['FECHA_VENCIMIENTO'], str):
                    registro.fecha_vencimiento = datetime.strptime(data['FECHA_VENCIMIENTO'], '%Y-%m-%d').date()
                else:
                    registro.fecha_vencimiento = data['FECHA_VENCIMIENTO']
            except (ValueError, TypeError):
                registro.fecha_vencimiento = None
        
        registro.accion = data.get('ACCION')
        registro.id_persona = data.get('ID_PERSONA')
        registro.id_carga = data.get('ID_CARGA')
        registro.id_poligono = data.get('ID_POLIGONO')
        
        # Convertir superficie a float si existe
        if data.get('SUPERFICIE'):
            try:
                registro.superficie = float(data['SUPERFICIE'])
            except (ValueError, TypeError):
                registro.superficie = None
                
        registro.coordenadas = data.get('COORDENADAS')
        registro.estatus = data.get('ESTATUS')
        
        # Campos adicionales (se pueden inicializar vacíos o según la lógica necesaria)
        registro.nuevo_estatus = data.get('NUEVO_ESTATUS', '')
        registro.descripcion = data.get('DESCRIPCION', '')
        registro.traslape = data.get('TRASLAPE', '')
        registro.fo_con_xx = data.get('FO_CON_XX', '')
        
        return registro 