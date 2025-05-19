from datetime import datetime
from utils.database import db

# Definición del modelo para la base de datos
class Poligono(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Columnas específicas mapeadas desde el Excel/Lista
    id_poligono = db.Column(db.Text, nullable=True)
    if_val = db.Column(db.Text, nullable=True) # 'if' es palabra reservada
    id_credito = db.Column(db.Text, nullable=True)
    id_persona = db.Column(db.Text, nullable=True)
    superficie = db.Column(db.Float, nullable=True) # Asumiendo numérico
    estado = db.Column(db.Text, nullable=True)
    municipio = db.Column(db.Text, nullable=True)
    coordenadas = db.Column(db.Text, nullable=True) # Coordenadas originales
    coordenadas_corregidas = db.Column(db.Text, nullable=True) # Coordenadas decimales corregidas
    area_digitalizada = db.Column(db.Float, nullable=True) # Área calculada/editada
    estatus = db.Column(db.Text, nullable=True) # Estatus (si existe)
    comentarios = db.Column(db.Text, nullable=True) # Comentarios editables
    descripcion = db.Column(db.Text, nullable=True) # Nueva columna para descripción
    # Metadata
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 