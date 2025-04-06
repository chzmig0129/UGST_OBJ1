from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import pandas as pd
import numpy as np
import re
import json
from werkzeug.utils import secure_filename
from flask import jsonify
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from shapely.geometry import Polygon, Point
from geopy.distance import geodesic
import geopandas as gpd
import shapefile
import tempfile
import zipfile
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB límite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///poligonos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False  # Permitir caracteres UTF-8 en respuestas JSON

# Añadir filtro personalizado para slice
@app.template_filter('slice')
def slice_filter(iterable, start, end=None):
    if iterable is None or len(iterable) == 0:
        return []
    if end is None:
        return iterable[start:]
    return iterable[start:end]

# Cargar shapefile de municipios de México
try:
    municipios_gdf = gpd.read_file("data/mun22gw.shp")
    # Verificar/convertir CRS a WGS84 (EPSG:4326)
    if municipios_gdf.crs != "EPSG:4326":
        municipios_gdf = municipios_gdf.to_crs(epsg=4326)
    # Filtrar solo columnas necesarias para optimizar
    municipios_gdf = municipios_gdf[["NOMGEO", "NOM_ENT", "geometry"]]
    print("Shapefile de municipios cargado correctamente. Columnas:", municipios_gdf.columns.tolist())
except Exception as e:
    print(f"Error cargando shapefile: {e}")
    municipios_gdf = None

# Función para obtener municipio y estado desde coordenadas
def obtener_ubicacion(lat, lon):
    if municipios_gdf is None:
        return None
    try:
        punto = Point(lon, lat)  # Shapely usa (x=lon, y=lat)
        mask = municipios_gdf.contains(punto)
        resultados = municipios_gdf[mask]
        if not resultados.empty:
            # Corregir la codificación de caracteres
            municipio = resultados.iloc[0]["NOMGEO"]
            estado = resultados.iloc[0]["NOM_ENT"]
            
            # Intentar corregir la codificación si es necesario
            try:
                # Si los nombres están en Latin-1 pero interpretados como UTF-8
                if isinstance(municipio, str) and any(c in municipio for c in ['Ã', 'Â', 'Á', 'É', 'Í', 'Ó', 'Ú']):
                    municipio = municipio.encode('latin-1').decode('utf-8')
                if isinstance(estado, str) and any(c in estado for c in ['Ã', 'Â', 'Á', 'É', 'Í', 'Ó', 'Ú']):
                    estado = estado.encode('latin-1').decode('utf-8')
            except Exception as encoding_error:
                print(f"Error al corregir codificación: {encoding_error}")
                
            return {
                "municipio": municipio,
                "estado": estado
            }
    except Exception as e:
        print(f"Error al obtener ubicación: {e}")
    return None

db = SQLAlchemy(app)

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
    # Metadata
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Variable global para almacenar los datos del Excel (mantener por compatibilidad)
excel_data = {
    'data': [],
    'columns': [],
    'filename': '',
    'original_coords': []  # Nuevo: almacen coordenadas originales
}

# Asegurar que exista el directorio de uploads
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Eliminar la base de datos existente para forzar recreación
db_path = 'poligonos.db'
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Base de datos eliminada: {db_path}")
    except Exception as e:
        print(f"No se pudo eliminar la base de datos: {e}")

# Crear todas las tablas de la base de datos
with app.app_context():
    try:
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('poligono')
        column_names = [col['name'] for col in columns]
        print(f"Columnas existentes en la tabla 'poligono': {column_names}")
        
        # Verificar que existan las columnas esperadas (NUEVA ESTRUCTURA)
        required_db_columns = {
            'id', 'id_poligono', 'if_val', 'id_credito', 'id_persona',
            'superficie', 'estado', 'municipio', 'coordenadas',
            'coordenadas_corregidas', 'area_digitalizada', 'estatus',
            'comentarios', 'fecha_creacion', 'fecha_modificacion'
        }
        current_db_columns = set(column_names)
        
        if current_db_columns != required_db_columns:
            print("Estructura de tabla desactualizada o incorrecta. Recreando tablas...")
            db.drop_all()
            db.create_all()
            print("Tablas recreadas correctamente con la nueva estructura.")
        else:
            print("Estructura de tabla correcta.")
            
    except Exception as e:
        print(f"Error al verificar/crear estructura de la base de datos: {e}")
        print("Intentando crear las tablas de todos modos...")
        # Si hay error (p.ej., la tabla no existe), intentamos crearla
        try:
            db.create_all()
            print("db.create_all() ejecutado.")
        except Exception as create_e:
            print(f"Error fatal al intentar crear las tablas: {create_e}")

    print("Base de datos inicializada.")

# ==============================================
# Funciones para procesamiento de coordenadas
# ==============================================

def limpiar_coordenada(coord):
    coord = coord.replace('\t', '').replace('"', '').strip()
    coord = re.sub(' +', ' ', coord)
    return coord

def corregir_longitud(coord_decimales):
    if pd.isna(coord_decimales) or coord_decimales == '':
        return coord_decimales
        
    coord_list = coord_decimales.split(' | ')
    corrected_coords = []
    for coord in coord_list:
        if ',' not in coord:
            continue
        lat, lon = coord.split(',')
        try:
            lat = float(lat.strip())
            lon = float(lon.strip())

            if lon > 0:
                lon *= -1

            corrected_coords.append(f"{lat:.6f},{lon:.6f}")  # Más precisión
        except:
            continue

    return ' | '.join(corrected_coords)

def dms_a_decimal(coord):
    try:
        # Primero identificar la dirección (N, S, E, W)
        match_dir = re.search(r'([NSEW])$', coord.strip(), re.IGNORECASE)
        direccion = match_dir.group(1).upper() if match_dir else ''
        
        # Caso especial: formato compacto tipo 18°4811.1N (sin separadores entre minutos y segundos)
        special_match = re.match(r'(\d+)[°\s](\d{2})(\d{2}\.\d+)([NSEW])', coord)
        if special_match:
            grados = float(special_match.group(1))
            minutos = float(special_match.group(2))
            segundos = float(special_match.group(3))
            direccion = special_match.group(4).upper()
            
            decimal = grados + minutos/60 + segundos/3600
            if direccion in ['S', 'W']:
                decimal *= -1
            return round(decimal, 6)
            
        # Caso normal: formato separado por símbolos tradicionales
        coord_num = re.sub(r'[^\d\.\-]', ' ', coord)
        parts = coord_num.strip().split()
        
        if len(parts) == 3:
            grados, minutos, segundos = map(float, parts)
        elif len(parts) == 2:
            grados, minutos = map(float, parts)
            segundos = 0.0
        elif len(parts) == 1:
            # Intento detectar formato compacto dentro de un solo número (ej: 184811.1)
            part = parts[0]
            if len(part) >= 4:  # Al menos debe tener grados (2) y minutos (2)
                try:
                    # Intenta interpretar como GGMMSS.S
                    if '.' in part:
                        dot_pos = part.index('.')
                        # Si hay suficientes dígitos antes del punto para grados(2) + minutos(2)
                        if dot_pos >= 4:
                            grados = float(part[:dot_pos-4])
                            minutos = float(part[dot_pos-4:dot_pos-2])
                            segundos = float(part[dot_pos-2:])
                        else:
                            grados = float(part[:2])
                            minutos = float(part[2:4])
                            segundos = float('0.' + part.split('.')[1])
                    else:
                        # Sin punto decimal, interpretar como GGMMSS
                        grados = float(part[:2])
                        minutos = float(part[2:4])
                        if len(part) > 4:
                            segundos = float(part[4:])
                        else:
                            segundos = 0.0
                    
                    decimal = grados + minutos/60 + segundos/3600
                    if direccion in ['S', 'W']:
                        decimal *= -1
                    return round(decimal, 6)
                except:
                    grados = float(part)
                    minutos = segundos = 0.0
            else:
                grados = float(part)
                minutos = segundos = 0.0
        else:
            return np.nan
            
        decimal = grados + minutos/60 + segundos/3600
        if direccion in ['S', 'W']:
            decimal *= -1
        return round(decimal, 6)  # Más precisión
    except Exception as e:
        print(f"Error al convertir DMS a decimal: {coord} - {str(e)}")
        return np.nan

def es_dms(coord):
    # Verificar si tiene símbolos de grados, minutos o segundos
    if re.search('[°\'"]', coord):
        return True
    # Verificar si tiene dirección N, S, E, W
    if re.search(r'[NSEW]$', coord, re.IGNORECASE):
        return True
    # Verificar formato de números separados
    coord_num = re.sub(r'[^\d\.]', ' ', coord)
    parts = coord_num.strip().split()
    return len(parts) > 1

def procesar_coordenadas_dms(fila):
    if 'COORDENADAS' not in fila or pd.isna(fila['COORDENADAS']):
        return ''
    
    coordenadas = str(fila['COORDENADAS'])
    coordenadas = coordenadas.replace('\n', ' ').replace('\r', ' ').strip()
    
    # Dividir por múltiples posibles separadores
    for sep in ['|', ';', ' y ', ',y,']:
        if sep in coordenadas:
            coord_list = coordenadas.split(sep)
            break
    else:
        # Si no se encontró ningún separador común, intentar dividir por espacios
        if ' ' in coordenadas and ',' not in coordenadas:
            # Asumir que cada par de coordenadas está separado por espacios
            parts = coordenadas.split()
            if len(parts) % 2 == 0:  # Debe haber un número par de partes
                coord_list = []
                for i in range(0, len(parts), 2):
                    if i+1 < len(parts):
                        coord_list.append(f"{parts[i]} {parts[i+1]}")
            else:
                coord_list = [coordenadas]  # Un solo par de coordenadas
        else:
            coord_list = [coordenadas]  # Un solo par de coordenadas
    
    coord_list = [c.strip() for c in coord_list]
    
    # Depuración para ver las coordenadas procesadas
    print(f"Coordenadas divididas: {coord_list}")
    
    coords_decimales = []
    
    for coord_pair in coord_list:
        coord_pair = coord_pair.strip()
        if not coord_pair:
            continue
        
        # Casos especiales: coordenadas tipo 18°4811.1N,103°5102.7W
        special_match = re.match(r'(\d+[°\s]\d{2}\d{2}\.\d+[NSEW])[,\s]+(\d+[°\s]\d{2}\d{2}\.\d+[NSEW])', coord_pair)
        if special_match:
            lat_str = special_match.group(1)
            lon_str = special_match.group(2)
            try:
                lat = dms_a_decimal(lat_str)
                lon = dms_a_decimal(lon_str)
                if not np.isnan(lat) and not np.isnan(lon):
                    coords_decimales.append(f"{lat:.6f},{lon:.6f}")
                    print(f"Par procesado especial: {lat_str},{lon_str} -> {lat:.6f},{lon:.6f}")
                continue
            except Exception as e:
                print(f"Error procesando formato especial {coord_pair}: {e}")
            
        # Procesamiento normal
        if ' ' in coord_pair and ',' not in coord_pair:
            parts = coord_pair.split()
            
            patterns = [
                r'([0-9\.]+[°][0-9\.]+[\'"][0-9\.]*[\"]*[NS])\s+([0-9\.]+[°][0-9\.]+[\'"][0-9\.]*[\"]*[WE])',
                r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s*[NS])\s+([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s*[WE])',
                r'([0-9\.]+\s+[0-9\.]+\s*[NS])\s+([0-9\.]+\s+[0-9\.]+\s*[WE])',
                r'([0-9\.]+\s*[NS])\s+([0-9\.]+\s*[WE])',
                # Formatos para 18°4811.1N
                r'(\d+[°\s]\d{2}\d{2}\.\d+[NS])\s+(\d+[°\s]\d{2}\d{2}\.\d+[WE])'
            ]
            
            lat_str = None
            lon_str = None
            
            for pattern in patterns:
                match = re.search(pattern, coord_pair)
                if match:
                    lat_str, lon_str = match.groups()
                    break
                    
            if lat_str is None or lon_str is None:
                lat_parts = [p for p in parts if 'N' in p.upper() or 'S' in p.upper()]
                lon_parts = [p for p in parts if 'W' in p.upper() or 'E' in p.upper()]
                
                if len(lat_parts) == 1 and len(lon_parts) == 1:
                    lat_str = lat_parts[0]
                    lon_str = lon_parts[0]
                elif len(parts) >= 2:
                    mid = len(parts) // 2
                    lat_str = ' '.join(parts[:mid])
                    lon_str = ' '.join(parts[mid:])
                else:
                    continue
                    
        elif ',' in coord_pair:
            try:
                lat_str, lon_str = coord_pair.split(',', 1)
            except:
                continue
        else:
            # Intentar interpretar como un formato especial sin espacios ni comas
            match = re.match(r'(\d+[°\s]\d+\.\d+[NS])(\d+[°\s]\d+\.\d+[WE])', coord_pair)
            if match:
                lat_str, lon_str = match.groups()
            elif re.search(r'[NS]', coord_pair, re.IGNORECASE) and re.search(r'[WE]', coord_pair, re.IGNORECASE):
                # Intentar encontrar donde termina la latitud (marcada por N o S) y empieza longitud
                ns_pos = max(coord_pair.upper().rfind('N'), coord_pair.upper().rfind('S'))
                if ns_pos > 0:
                    lat_str = coord_pair[:ns_pos+1]
                    lon_str = coord_pair[ns_pos+1:]
                else:
                    continue
            else:
                if re.search(r'[0-9]', coord_pair):
                    try:
                        coords_clean = re.sub(r'[^\d\.\-]', ' ', coord_pair)
                        nums = [float(x) for x in coords_clean.split() if x.strip()]
                        if len(nums) >= 2:
                            lat, lon = nums[0], nums[1]
                            if lon > 0 and lon > 90:
                                lon *= -1
                            coords_decimales.append(f"{lat:.6f},{lon:.6f}")
                    except Exception as e:
                        print(f"Error procesando parte numérica {coord_pair}: {e}")
                continue

        # Limpieza adicional
        lat_str = limpiar_coordenada(lat_str) if lat_str else ''
        lon_str = limpiar_coordenada(lon_str) if lon_str else ''
        
        # Intentar procesarlas como DMS
        print(f"Procesando: lat_str={lat_str}, lon_str={lon_str}")
        
        try:
            # Proceso de latitud
            if es_dms(lat_str):
                lat = dms_a_decimal(lat_str)
                print(f"Latitud DMS: {lat_str} -> {lat}")
            else:
                lat_str_numeric = re.sub(r'[^\d\.\-]', '', lat_str)
                lat = float(lat_str_numeric)
                if 'S' in lat_str.upper():
                    lat *= -1
                print(f"Latitud decimal: {lat_str} -> {lat}")
                
            if np.isnan(lat):
                print(f"Latitud inválida: {lat_str}")
                continue
        except Exception as e:
            print(f"Error procesando latitud {lat_str}: {e}")
            continue

        try:
            # Proceso de longitud
            if es_dms(lon_str):
                lon = dms_a_decimal(lon_str)
                print(f"Longitud DMS: {lon_str} -> {lon}")
            else:
                lon_str_numeric = re.sub(r'[^\d\.\-]', '', lon_str)
                lon = float(lon_str_numeric)
                if 'W' in lon_str.upper():
                    lon *= -1
                elif lon > 0:
                    lon *= -1  # Asumir oeste para América
                print(f"Longitud decimal: {lon_str} -> {lon}")
                
            if np.isnan(lon):
                print(f"Longitud inválida: {lon_str}")
                continue
        except Exception as e:
            print(f"Error procesando longitud {lon_str}: {e}")
            continue

        if not np.isnan(lat) and not np.isnan(lon):
            coords_decimales.append(f"{lat:.6f},{lon:.6f}")
            print(f"Par añadido: {lat:.6f},{lon:.6f}")

    # Eliminar duplicados
    coords_decimales = list(dict.fromkeys(coords_decimales))
    return ' | '.join(coords_decimales)

def calcular_area_poligono(coordenadas_str):
    """Calcula el área de un polígono en hectáreas usando cálculo geodésico"""
    if not coordenadas_str:
        return 0.0
    
    try:
        from shapely.geometry import Polygon
        from geopy.distance import geodesic
        import numpy as np
        
        # Parsear coordenadas - Soportar tanto | como espacios como separadores
        points = []
        # Determinar si se usa | o espacios como separador
        separador = '|' if '|' in coordenadas_str else ' '
        
        for pair in coordenadas_str.split(separador):
            if not pair.strip():
                continue
            parts = pair.strip().split(',')
            if len(parts) >= 2:
                try:
                    lat, lon = map(float, parts[:2])
                    points.append((lat, lon))
                except (ValueError, TypeError):
                    # Ignorar coordenadas inválidas
                    continue
        
        if len(points) < 3:
            return 0.0
        
        # Implementación del algoritmo geodésico para calcular área
        # Basado en el cálculo que usa Leaflet.GeometryUtil.geodesicArea
        area = 0.0
        coords = np.array(points)
        
        if len(coords) > 2:
            p1 = coords[0]
            for i in range(1, len(coords) - 1):
                p2 = coords[i]
                p3 = coords[i + 1]
                
                # Cálculo del área del triángulo geodésico usando la fórmula del semiperímetro
                a = geodesic(p1, p2).meters
                b = geodesic(p2, p3).meters
                c = geodesic(p3, p1).meters
                s = (a + b + c) / 2.0
                
                # Fórmula de Herón (evitar números negativos bajo la raíz)
                area_factor = s * (s - a) * (s - b) * (s - c)
                if area_factor > 0:
                    area_triangulo = np.sqrt(area_factor)
                    area += area_triangulo
                else:
                    # Si el factor es negativo, usar un enfoque alternativo o 0
                    print(f"Factor de área negativo: {area_factor}")
        
        # Convertir a hectáreas (1 ha = 10,000 m²)
        return area / 10000.0
    except Exception as e:
        print(f"Error al calcular área geodésica: {e}")
        
        # Fallback: usar shapely para cálculo plano si el geodésico falla
        try:
            from shapely.geometry import Polygon
            coords = []
            
            # Determinar si se usa | o espacios como separador
            separador = '|' if '|' in coordenadas_str else ' '
            
            for pair in coordenadas_str.split(separador):
                if not pair.strip():
                    continue
                parts = pair.strip().split(',')
                if len(parts) >= 2:
                    try:
                        lat, lon = map(float, parts[:2])
                        coords.append((lon, lat))  # Shapely usa (x,y) = (lon,lat)
                    except (ValueError, TypeError):
                        # Ignorar coordenadas inválidas
                        continue
            
            if len(coords) < 3:
                return 0.0
                
            try:
                polygon = Polygon(coords)
                if polygon.is_valid:
                    return polygon.area / 10000  # Convertir m² a hectáreas
                else:
                    print("Polígono inválido, regresando área 0")
                    return 0.0
            except:
                print("No se pudo crear polígono válido, regresando área 0")
                return 0.0
        except Exception as inner_e:
            print(f"Error en fallback de cálculo de área: {inner_e}")
            return 0.0

# ==============================================
# Rutas de la aplicación
# ==============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validacion-rapida')
def validacion_rapida():
    return "Página de validación rápida en desarrollo"

@app.route('/unir-archivos')
def unir_archivos():
    return "Página para unir archivos SHP en desarrollo"

@app.route('/validacion-poligonos', defaults={'tab': 'cargar'})
@app.route('/validacion-poligonos/<tab>')
def validacion_poligonos(tab):
    valid_tabs = ['cargar', 'lista', 'editar', 'generar']
    
    if tab not in valid_tabs:
        tab = 'cargar'
    
    if tab == 'lista':
        try:
            # Obtener datos de la base de datos
            print("Consultando polígonos en la base de datos...")
            poligonos = Poligono.query.all()
            print(f"Se encontraron {len(poligonos)} polígonos en la base de datos")
            
            # Convertir a formato compatible con la plantilla (LEYENDO DIRECTO DE COLUMNAS)
            data = []
            for p in poligonos:
                # Crear diccionario directamente desde los atributos del objeto Poligono
                datos = {
                    'ID_POLIGONO': p.id_poligono,
                    'IF': p.if_val,
                    'ID_CREDITO': p.id_credito,
                    'ID_PERSONA': p.id_persona,
                    'SUPERFICIE': p.superficie,
                    'ESTADO': corregir_codificacion(p.estado),
                    'MUNICIPIO': corregir_codificacion(p.municipio),
                    'COORDENADAS': p.coordenadas,
                    'COORDENADAS_CORREGIDAS': p.coordenadas_corregidas,
                    'AREA_DIGITALIZADA': p.area_digitalizada,
                    'ESTATUS': p.estatus,
                    'COMENTARIOS': p.comentarios,
                    'db_id': p.id # ID de la base de datos
                }
                # Ya no es necesario cargar JSON ni usar setdefault,
                # los atributos no presentes en BD serán None por defecto.
                data.append(datos)
            
            # --- Definir columnas fijas para la vista de lista ---
            columns_to_display = [
                'ID_POLIGONO', 'IF', 'ID_CREDITO', 'ID_PERSONA', 'SUPERFICIE',
                'ESTADO', 'MUNICIPIO', 'COORDENADAS', 'COORDENADAS_CORREGIDAS',
                'AREA_DIGITALIZADA', 'ESTATUS', 'COMENTARIOS', 'db_id' # Añadir COMENTARIOS
            ]
            # --- FIN: Definir columnas fijas ---

            print(f"Mostrando {len(columns_to_display)} columnas fijas: {columns_to_display}")

            return render_template('validacion_poligonos.html',
                               tab=tab,
                               data=data,
                               columns=columns_to_display, # Usar la lista fija
                               filename=excel_data['filename']) # Mantener filename por compatibilidad
        except Exception as e:
            print(f"ERROR AL CARGAR LISTA: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error al cargar datos: {str(e)}', 'error')
            return render_template('validacion_poligonos.html', 
                               tab=tab, 
                               data=[],
                               columns=[],
                               filename='')
    
    elif tab == 'editar':
        row_index = request.args.get('id', type=int)
        db_id = request.args.get('db_id', type=int)
        
        try:
            # Si tenemos db_id, usamos la base de datos
            if db_id is not None:
                print(f"Editando polígono con ID de base de datos: {db_id}")
                poligono = Poligono.query.get(db_id)
                if poligono is None:
                    flash('Registro no encontrado en la base de datos', 'error')
                    return redirect(url_for('validacion_poligonos', tab='lista'))
                
                # Cargar datos directamente desde el objeto Poligono
                row_data = {
                    'ID_POLIGONO': poligono.id_poligono,
                    'IF': poligono.if_val,
                    'ID_CREDITO': poligono.id_credito,
                    'ID_PERSONA': poligono.id_persona,
                    'SUPERFICIE': poligono.superficie,
                    'ESTADO': corregir_codificacion(poligono.estado),
                    'MUNICIPIO': corregir_codificacion(poligono.municipio),
                    'COORDENADAS': poligono.coordenadas, # Mantener coordenadas originales
                    'COORDENADAS_DECIMALES_CORREGIDAS': poligono.coordenadas_corregidas, # Mantener el nombre usado en frontend
                    'AREA_DIGITALIZADA': poligono.area_digitalizada, # Campo editable
                    'ESTATUS': poligono.estatus,
                    'COMENTARIOS': poligono.comentarios, # Campo editable
                    'db_id': poligono.id
                }
                
                # Calcular área
                area_ha = calcular_area_poligono(poligono.coordenadas_corregidas)
                
                # Formatear datos numéricos para la vista
                row_data['AREA_CALCULADA'] = f"{area_ha:.4f}" # Área calculada a partir de coordenadas
                
                # Si ya hay un área digitalizada guardada, mostrarla formateada
                if poligono.area_digitalizada is not None:
                    row_data['AREA_DIGITALIZADA'] = f"{poligono.area_digitalizada:.4f}"
                else:
                    # Si no hay área guardada, usar la calculada
                    row_data['AREA_DIGITALIZADA'] = row_data['AREA_CALCULADA']

                # Asegurarse que los valores de estado y municipio no sean None
                if not row_data['ESTADO']: row_data['ESTADO'] = ''
                if not row_data['MUNICIPIO']: row_data['MUNICIPIO'] = ''
                if not row_data['COMENTARIOS']: row_data['COMENTARIOS'] = ''
                
                # NUEVO: Obtener municipio y estado desde coordenadas si no están definidos
                if (not row_data['ESTADO'] or not row_data['MUNICIPIO']) and poligono.coordenadas_corregidas:
                    ubicacion = obtener_ubicacion_desde_poligono(poligono.coordenadas_corregidas)
                    if ubicacion:
                        # Solo actualizar si no están definidos
                        if not row_data['MUNICIPIO']:
                            row_data['MUNICIPIO'] = ubicacion['municipio']
                        if not row_data['ESTADO']:
                            row_data['ESTADO'] = ubicacion['estado']
                        
                        # Agregar una bandera para indicar que se determinó automáticamente
                        row_data['UBICACION_AUTO'] = True
                
                # Preprocesar coordenadas para el mapa
                coords_para_mapa = []
                if poligono.coordenadas_corregidas:
                    try:
                        coord_pairs = poligono.coordenadas_corregidas.split(' | ')
                        for pair in coord_pairs:
                            if ',' in pair:
                                lat_str, lon_str = pair.split(',')
                                lat = float(lat_str.strip())
                                lon = float(lon_str.strip())
                                coords_para_mapa.append([lat, lon])
                    except Exception as e:
                        print(f"Error al procesar coordenadas para mapa: {e}")

                # Determinar columnas para edición (basado en lo que ahora está en row_data)
                edit_columns = list(row_data.keys()) # Simplificado: mostrar todos los campos cargados

                return render_template('validacion_poligonos.html',
                                   tab=tab,
                                   row_data=row_data,
                                   row_index=row_index, # Mantener por compatibilidad si se necesita
                                   db_id=db_id,
                                   coords_para_mapa=coords_para_mapa,
                                   columns=edit_columns) # Mostrar todas las columnas recuperadas
            
            # Compatibilidad con el código anterior (se podría eliminar si ya no se usa)
            elif row_index is not None and row_index < len(excel_data['data']):
                print(f"Editando polígono desde memoria con índice: {row_index}")
                row_data = excel_data['data'][row_index]
                
                # Calcular área
                area_ha = calcular_area_poligono(row_data.get('COORDENADAS_DECIMALES_CORREGIDAS', ''))
                row_data['AREA_DIGITALIZADA'] = f"{area_ha:.2f}"
                
                return render_template('validacion_poligonos.html', 
                                   tab=tab, 
                                   row_data=row_data,
                                   row_index=row_index,
                                   columns=excel_data['columns'])
            
            else:
                flash('Índice de fila inválido', 'error')
                return redirect(url_for('validacion_poligonos', tab='lista'))
        except Exception as e:
            print(f"ERROR AL EDITAR: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error al editar polígono: {str(e)}', 'error')
            return redirect(url_for('validacion_poligonos', tab='lista'))
    
    elif tab == 'generar':
        try:
            # Obtener datos de la base de datos para generar reportes
            poligonos = Poligono.query.all()
            
            # Convertir a formato compatible con la plantilla (LEYENDO DIRECTO DE COLUMNAS)
            data = []
            for p in poligonos:
                # Crear diccionario directamente desde los atributos del objeto Poligono
                datos = {
                    'ID_POLIGONO': p.id_poligono,
                    'IF': p.if_val,
                    'ID_CREDITO': p.id_credito,
                    'ID_PERSONA': p.id_persona,
                    'SUPERFICIE': p.superficie,
                    'ESTADO': corregir_codificacion(p.estado),
                    'MUNICIPIO': corregir_codificacion(p.municipio),
                    'COORDENADAS': p.coordenadas,
                    'COORDENADAS_CORREGIDAS': p.coordenadas_corregidas,
                    'AREA_DIGITALIZADA': p.area_digitalizada,
                    'ESTATUS': p.estatus,
                    'COMENTARIOS': p.comentarios,
                    'db_id': p.id
                }
                data.append(datos)
            
            # Si no hay datos en la base de datos, usar datos en memoria (mantener por si acaso)
            if not data and excel_data.get('data'):
                data = excel_data['data']
                flash('Generando reporte con datos en memoria. No hay datos guardados en la base de datos.', 'warning')
            
            # Asegurar que haya datos para prevenir división por cero
            if not data:
                flash('No hay datos disponibles para generar reportes. Por favor, cargue un archivo primero.', 'warning')
                return redirect(url_for('validacion_poligonos', tab='cargar'))
            
            # Determinar columnas disponibles de manera segura
            all_columns = set()
            for row in data:
                if isinstance(row, dict):  # Asegurar que row sea un diccionario
                    all_columns.update(row.keys())
            
            columns = sorted(list(all_columns)) if all_columns else []
            
            return render_template('validacion_poligonos.html', 
                               tab=tab,
                               data=data,
                               columns=columns)
        except Exception as e:
            print(f"ERROR AL GENERAR REPORTE: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error al generar reporte: {str(e)}', 'error')
            return redirect(url_for('validacion_poligonos', tab='lista'))
    
    else:  # tab == 'cargar'
        columnas_ejemplo = [
            'ID_POLIGONO', 'ESTADO', 'AREA_REPORTADA', 'AREA_DIGITALIZADA',
            'COORDENADAS', 'MUNICIPIO', 'ID_CREDITO_FIRA', 'ID_PERSONA',
            'NOMBRE_IF', 'OBSERVACIONES', 'COMENTARIOS', 'CURP_PRODUCTOR', 'RFC'
        ]
        return render_template('validacion_poligonos.html', 
                           tab=tab,
                           columnas=columnas_ejemplo,
                           uploaded_columns=excel_data['columns'],
                           filename=excel_data['filename'])

@app.route('/cargar-excel', methods=['POST'])
def cargar_excel():
    global excel_data
    
    if 'archivo' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('validacion_poligonos'))
    
    archivo = request.files['archivo']
    
    if archivo.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('validacion_poligonos'))
    
    if archivo and allowed_file(archivo.filename):
        try:
            # Guardar el archivo
            filename = secure_filename(archivo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(filepath)
            
            # Leer el archivo Excel
            print(f"Leyendo archivo Excel: {filename}")
            df = pd.read_excel(filepath)
            print(f"Columnas encontradas en el Excel: {df.columns.tolist()}")
            
            # Normalizar nombres de columnas (eliminar espacios, convertir a mayúsculas)
            df.columns = [col.strip().upper().replace(' ', '_') for col in df.columns]
            print(f"Columnas normalizadas: {df.columns.tolist()}")
            
            # --- INICIO: Validar columnas requeridas ---
            required_columns = {'IF', 'ID_CREDITO', 'ID_PERSONA', 'ID_POLIGONO', 'SUPERFICIE', 'COORDENADAS'}
            actual_columns = set(df.columns)
            
            if actual_columns != required_columns:
                missing_cols = required_columns - actual_columns
                extra_cols = actual_columns - required_columns
                error_parts = []
                if missing_cols:
                    error_parts.append(f"Faltan columnas: {', '.join(sorted(list(missing_cols)))}")
                if extra_cols:
                    error_parts.append(f"Hay columnas extra: {', '.join(sorted(list(extra_cols)))}")

                error_msg = f"El excel no sigue el formato. Favor de verificar el nombre de las columnas. Columnas requeridas: {', '.join(sorted(list(required_columns)))}. Detalles: {'. '.join(error_parts)}"
                flash(error_msg, 'error')
                return redirect(url_for('validacion_poligonos', tab='cargar'))
            # --- FIN: Validar columnas requeridas ---

            # Asegurar que exista la columna COORDENADAS (Esta validación ya está cubierta arriba, se podría quitar pero la dejamos por si acaso)
            # if 'COORDENADAS' not in df.columns:
            #     # Buscar una columna que pueda contener coordenadas (buscar patrones como 26°47'54"N)
            #     for col in df.columns:
            #         if df[col].dtype == 'object' and df[col].astype(str).str.contains('°|\'|"|N|W', regex=True).any():
            #             print(f"Se encontró columna con posibles coordenadas: {col}")
            #             df['COORDENADAS'] = df[col]
            #             break
            #     
            #     if 'COORDENADAS' not in df.columns:
            #         flash('El archivo debe contener una columna con coordenadas', 'error')
            #         return redirect(url_for('validacion_poligonos'))
            
            # Procesar coordenadas
            df['COORDENADAS_DECIMALES'] = df.apply(procesar_coordenadas_dms, axis=1)
            df['COORDENADAS_DECIMALES_CORREGIDAS'] = df['COORDENADAS_DECIMALES'].apply(corregir_longitud)
            
            # No calculamos el área aquí, la dejamos como None inicialmente
            # df['AREA_DIGITALIZADA'] = areas

            # Limpiar variable global excel_data ya que usaremos la BD
            excel_data = {
                'data': [],
                'columns': [],
                'filename': filename, # Guardamos el nombre del último archivo cargado
                'original_coords': []
            }
            
            # GUARDAR EN LA BASE DE DATOS
            try:
                print("Intentando guardar datos en la base de datos...")
                # Primero limpiamos la tabla para evitar duplicaciones al cargar un nuevo archivo
                db.session.query(Poligono).delete()
                db.session.commit()
                print(f"Tabla 'poligono' limpiada. Insertando {len(df)} registros...")
                
                count = 0
                for index, row in df.iterrows():
                    # Crear objeto Poligono mapeando columnas del DF a atributos del modelo
                    # Usar .get() para manejar columnas opcionales en el Excel
                    try:
                        superficie_val = float(row.get('SUPERFICIE', None)) if pd.notna(row.get('SUPERFICIE')) else None
                    except (ValueError, TypeError):
                        superficie_val = None

                    poligono = Poligono(
                        id_poligono=str(row.get('ID_POLIGONO', '')),
                        if_val=str(row.get('IF', '')), # Mapeado a if_val
                        id_credito=str(row.get('ID_CREDITO', '')),
                        id_persona=str(row.get('ID_PERSONA', '')),
                        superficie=superficie_val,
                        estado=str(row.get('ESTADO', '')), # Añadir si existe en Excel
                        municipio=str(row.get('MUNICIPIO', '')), # Añadir si existe en Excel
                        coordenadas=str(row.get('COORDENADAS', '')),
                        coordenadas_corregidas=str(row.get('COORDENADAS_DECIMALES_CORREGIDAS', '')), # Usar las corregidas
                        area_digitalizada=None, # Se inicializa como None
                        estatus=str(row.get('ESTATUS', '')), # Añadir si existe en Excel
                        comentarios=None        # Se inicializa como None
                        # datos_json ya no existe
                    )
                    db.session.add(poligono)
                    count += 1

                    # Commit por lotes
                    if count % 100 == 0:
                        db.session.commit()
                        print(f"Guardados {count} registros...")
                
                # Commit final
                db.session.commit()
                print(f"¡Guardados {count} registros en total en la base de datos!")
                flash(f'Archivo \'{filename}\' cargado y {count} registros guardados en la base de datos', 'success')
                
            except Exception as db_error:
                print(f"ERROR AL GUARDAR EN LA BASE DE DATOS: {str(db_error)}")
                import traceback
                traceback.print_exc()
                flash(f'Error al guardar en la base de datos: {str(db_error)}', 'error')
                try:
                    db.session.rollback()
                except: pass
                # Redirigir a cargar si falla la BD
                return redirect(url_for('validacion_poligonos', tab='cargar'))
            
            # Redirigir a la lista después de guardar exitosamente
            return redirect(url_for('validacion_poligonos', tab='lista'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            print(f"ERROR GENERAL: {str(e)}")
            import traceback
            traceback.print_exc()
            return redirect(url_for('validacion_poligonos'))
    
    flash('Formato de archivo no permitido. Solo se aceptan .xlsx o .xls', 'error')
    return redirect(url_for('validacion_poligonos'))

@app.route('/actualizar-fila', methods=['POST'])
def actualizar_fila():
    global excel_data
    
    row_index = request.form.get('row_index', type=int)
    db_id = request.form.get('db_id', type=int)
    
    # Imprimir información de la solicitud para depuración
    print(f"Actualizando fila - db_id: {db_id}, row_index: {row_index}")
    print(f"Datos del formulario: {request.form}")
    
    try:
        # Si tenemos db_id, actualizamos en la base de datos
        if db_id is not None:
            poligono = Poligono.query.get(db_id)
            if poligono is None:
                flash('Registro no encontrado en la base de datos', 'error')
                return redirect(url_for('validacion_poligonos', tab='lista'))
            
            print(f"Actualizando polígono en la base de datos con ID: {db_id}")

            # Cargar datos JSON actuales -> YA NO SE USA JSON
            # try:
            #     datos_actuales = json.loads(poligono.datos_json)
            # except:
            #     datos_actuales = {}

            # Actualizar campos directamente en el objeto Poligono
            for campo_form, valor_form in request.form.items():
                # Evitar campos especiales
                if campo_form in ['row_index', 'db_id']:
                    continue

                # Mapear nombre de campo del formulario (UPPERCASE) a atributo del modelo (lowercase)
                atributo_modelo = None
                if campo_form == 'ID_POLIGONO': atributo_modelo = 'id_poligono'
                elif campo_form == 'IF': atributo_modelo = 'if_val'
                elif campo_form == 'ID_CREDITO': atributo_modelo = 'id_credito'
                elif campo_form == 'ID_PERSONA': atributo_modelo = 'id_persona'
                elif campo_form == 'SUPERFICIE': atributo_modelo = 'superficie'
                elif campo_form == 'ESTADO': atributo_modelo = 'estado'
                elif campo_form == 'MUNICIPIO': atributo_modelo = 'municipio'
                # COORDENADAS originales no se editan aquí
                elif campo_form == 'COORDENADAS_DECIMALES_CORREGIDAS': atributo_modelo = 'coordenadas_corregidas'
                elif campo_form == 'AREA_DIGITALIZADA': atributo_modelo = 'area_digitalizada'
                elif campo_form == 'ESTATUS': atributo_modelo = 'estatus'
                elif campo_form == 'COMENTARIOS': atributo_modelo = 'comentarios'
                # Añadir más mapeos si se agregan más campos editables

                if atributo_modelo:
                    try:
                        # Intentar convertir a float si es un campo numérico
                        if atributo_modelo in ['superficie', 'area_digitalizada']:
                            valor_actualizado = float(valor_form) if valor_form.strip() else None
                        else:
                            valor_actualizado = valor_form
                        setattr(poligono, atributo_modelo, valor_actualizado)
                        print(f"Actualizado {atributo_modelo} a: {valor_actualizado}")
                    except ValueError:
                         print(f"Error al convertir {campo_form} ('{valor_form}') a número para {atributo_modelo}. Se guarda como None/String.")
                         # Si falla la conversión numérica, decidir si guardar como None o string (depende del campo)
                         if atributo_modelo in ['superficie', 'area_digitalizada']:
                             setattr(poligono, atributo_modelo, None)
                         else: # Para campos de texto, guardar el valor original
                             setattr(poligono, atributo_modelo, valor_form)
                    except Exception as set_err:
                         print(f"Error al actualizar {atributo_modelo}: {set_err}")

            # Guardar explícitamente el área digitalizada del formulario (redundante con el bucle, pero asegura tipo)
            # if 'AREA_DIGITALIZADA' in request.form and request.form['AREA_DIGITALIZADA'].strip():
            #     try:
            #         area_manual = float(request.form['AREA_DIGITALIZADA'])
            #         poligono.area_digitalizada = area_manual
            #         # datos_actuales['AREA_DIGITALIZADA'] = area_manual # No más JSON
            #         print(f"Usando área ingresada manualmente: {area_manual} hectáreas")
            #     except ValueError:
            #         poligono.area_digitalizada = None # Poner None si no es válido

            # Actualizar coordenadas (redundante con el bucle)
            # if 'COORDENADAS_DECIMALES_CORREGIDAS' in request.form:
            #     nuevas_coords = request.form['COORDENADAS_DECIMALES_CORREGIDAS']
            #     poligono.coordenadas_corregidas = nuevas_coords
            #     # datos_actuales['COORDENADAS_DECIMALES_CORREGIDAS'] = nuevas_coords # No más JSON

            # Guardar los datos actualizados como JSON -> YA NO SE USA JSON
            # poligono.datos_json = json.dumps(datos_actuales, ensure_ascii=False)

            # Actualizar fecha de modificación
            poligono.fecha_modificacion = datetime.utcnow()
            
            # Guardar cambios en la base de datos
            try:
                db.session.commit()
                print("Cambios guardados exitosamente en la base de datos")
                flash('Cambios guardados correctamente en la base de datos', 'success')
            except Exception as db_error:
                print(f"Error al guardar en la base de datos: {db_error}")
                db.session.rollback()
                flash(f'Error al guardar en la base de datos: {str(db_error)}', 'error')
            
            return redirect(url_for('validacion_poligonos', tab='lista'))
        
        # Compatibilidad con el código anterior (mediante index)
        elif row_index is not None and row_index < len(excel_data['data']):
            print(f"Actualizando polígono en memoria con índice: {row_index}")
            
            # Actualizar todos los campos editables
            for col in excel_data['columns']:
                if col in request.form:
                    excel_data['data'][row_index][col] = request.form[col]
            
            # Guardar explícitamente el área digitalizada del formulario
            if 'AREA_DIGITALIZADA' in request.form and request.form['AREA_DIGITALIZADA'].strip():
                try:
                    area_manual = float(request.form['AREA_DIGITALIZADA'])
                    excel_data['data'][row_index]['AREA_DIGITALIZADA'] = area_manual
                    print(f"Usando área ingresada manualmente: {area_manual} hectáreas")
                except ValueError:
                    print("Valor de área digitalizada no válido")
            
            # Actualizar coordenadas si se proporcionaron
            if 'COORDENADAS_DECIMALES_CORREGIDAS' in request.form:
                excel_data['data'][row_index]['COORDENADAS_DECIMALES_CORREGIDAS'] = request.form['COORDENADAS_DECIMALES_CORREGIDAS']
                # Ya no recalculamos el área basada en coordenadas
            
            flash('Cambios guardados correctamente (modo memoria)', 'success')
            return redirect(url_for('validacion_poligonos', tab='lista'))
        
        else:
            flash('Índice de fila inválido', 'error')
            return redirect(url_for('validacion_poligonos', tab='lista'))
    
    except Exception as e:
        print(f"ERROR GENERAL AL ACTUALIZAR: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error al actualizar: {str(e)}', 'error')
        return redirect(url_for('validacion_poligonos', tab='lista'))

@app.route('/get-original-coords/<int:row_index>')
def get_original_coords(row_index):
    """Endpoint para obtener coordenadas originales (AJAX)"""
    # Intentar obtener el ID de la base de datos si está presente
    db_id = request.args.get('db_id', type=int)
    
    if db_id is not None:
        # Obtener de la base de datos
        poligono = Poligono.query.get(db_id)
        if poligono is None:
            return jsonify({'error': 'Registro no encontrado en la base de datos'}), 404
        
        return jsonify({
            'coordenadas': poligono.coordenadas_corregidas
        })
    elif row_index >= 0 and row_index < len(excel_data.get('original_coords', [])):
        # Obtener del almacenamiento en memoria (compatibilidad)
        return jsonify({
            'coordenadas': excel_data['original_coords'][row_index]
        })
    else:
        return jsonify({'error': 'Índice inválido'}), 404

@app.route('/diagnostico-poligono/<int:db_id>')
def diagnostico_poligono(db_id):
    """Endpoint para mostrar información de diagnóstico de un polígono"""
    poligono = Poligono.query.get(db_id)
    if poligono is None:
        return jsonify({'error': 'Registro no encontrado en la base de datos'}), 404
    
    # Devolver todos los datos del polígono para diagnosticar
    datos = {
        'id': poligono.id,
        'id_poligono': poligono.id_poligono,
        'if_val': poligono.if_val,
        'id_credito': poligono.id_credito,
        'id_persona': poligono.id_persona,
        'superficie': poligono.superficie,
        'estado': poligono.estado,
        'municipio': poligono.municipio,
        'coordenadas': poligono.coordenadas,
        'coordenadas_corregidas': poligono.coordenadas_corregidas,
        'area_digitalizada': poligono.area_digitalizada,
        'estatus': poligono.estatus,
        'comentarios': poligono.comentarios,
        'fecha_creacion': str(poligono.fecha_creacion),
        'fecha_modificacion': str(poligono.fecha_modificacion)
    }
    
    return jsonify(datos)

@app.route('/obtener_ubicacion', methods=['POST'])
def get_ubicacion():
    """Endpoint para obtener municipio y estado desde coordenadas"""
    try:
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        
        # Usar la función para obtener el municipio y estado
        ubicacion = obtener_ubicacion(lat, lon)
        
        if ubicacion:
            return jsonify(ubicacion)
        return jsonify({"error": "Ubicación no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": f"Datos inválidos: {str(e)}"}), 400

# Función para obtener ubicación desde las coordenadas de un polígono
def obtener_ubicacion_desde_poligono(coordenadas_str):
    """Obtiene el municipio y estado desde las coordenadas de un polígono"""
    if not coordenadas_str:
        return None
    
    try:
        # Usar el primer punto del polígono para determinar ubicación
        coords_list = coordenadas_str.split(' | ')
        if not coords_list:
            return None
            
        first_point = coords_list[0].split(',')
        if len(first_point) < 2:
            return None
            
        lat = float(first_point[0])
        lon = float(first_point[1])
        
        ubicacion = obtener_ubicacion(lat, lon)
        if ubicacion:
            # Asegurar que los nombres tengan codificación correcta
            ubicacion['municipio'] = corregir_codificacion(ubicacion['municipio'])
            ubicacion['estado'] = corregir_codificacion(ubicacion['estado'])
        return ubicacion
    except Exception as e:
        print(f"Error al obtener ubicación desde polígono: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

@app.route('/generar_shapefiles', methods=['POST'])
def generar_shapefiles():
    """Ruta para generar archivos shapefile de polígonos seleccionados"""
    # Obtener los índices de polígonos seleccionados
    selected_rows = request.json.get('selected_rows', [])
    
    if not selected_rows:
        return jsonify({'error': 'No se seleccionaron polígonos'}), 400
    
    try:
        # Preparar un archivo ZIP en memoria para contener todos los shapefiles
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            # Para cada polígono seleccionado
            for row_id in selected_rows:
                # Buscar el polígono en la base de datos por su ID
                try:
                    row_id = int(row_id)
                    # Primero intentar buscar por ID exacto
                    poligono = Poligono.query.get(row_id)
                    
                    if poligono is None:
                        # Si no se encuentra, imprimir para depuración
                        print(f"No se encontró polígono con ID {row_id}, buscando en posición")
                        
                        # Intentar buscar por posición como fallback
                        poligonos = Poligono.query.all()
                        if 0 <= row_id < len(poligonos):
                            poligono = poligonos[row_id]
                        else:
                            print(f"Índice {row_id} fuera de rango, hay {len(poligonos)} polígonos")
                            continue
                    
                    print(f"Generando shapefile para polígono ID={poligono.id}, ID_POLIGONO={poligono.id_poligono}")
                except Exception as e:
                    print(f"Error al recuperar polígono {row_id}: {e}")
                    # Si no es un índice válido, continuar con el siguiente
                    continue
                
                # Generar shapefile para este polígono
                shapefile_buffer = generar_shapefile_individual(poligono, f'polygon-{row_id}')
                
                # Añadir el shapefile al archivo ZIP
                if shapefile_buffer:
                    zf.writestr(f'polygon-{row_id}.zip', shapefile_buffer.getvalue())
        
        # Regresar al inicio del archivo en memoria
        memory_file.seek(0)
        
        # Enviar el archivo ZIP como respuesta
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='poligonos_shapefiles.zip'
        )
    
    except Exception as e:
        print(f"Error al generar shapefiles: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/generar_paquete_completo', methods=['POST'])
def generar_paquete_completo():
    """Ruta para generar un paquete completo con fichas PDF y shapefiles"""
    # Obtener los índices de polígonos seleccionados
    selected_rows = request.json.get('selected_rows', [])
    
    if not selected_rows:
        return jsonify({'error': 'No se seleccionaron polígonos'}), 400
    
    try:
        # Preparar un archivo ZIP en memoria para contener todos los archivos
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            # Crear carpeta para fichas técnicas
            zf.writestr('fichas_tecnicas/', '')
            # Crear carpeta para shapefiles
            zf.writestr('shapefiles/', '')
            
            # Para cada polígono seleccionado
            for row_id in selected_rows:
                try:
                    row_id = int(row_id)
                    # Primero intentar buscar por ID exacto
                    poligono = Poligono.query.get(row_id)
                    
                    if poligono is None:
                        # Si no se encuentra, imprimir para depuración
                        print(f"No se encontró polígono con ID {row_id}, buscando en posición")
                        
                        # Intentar buscar por posición como fallback
                        poligonos = Poligono.query.all()
                        if 0 <= row_id < len(poligonos):
                            poligono = poligonos[row_id]
                        else:
                            print(f"Índice {row_id} fuera de rango, hay {len(poligonos)} polígonos")
                            continue
                            
                    print(f"Generando fichas para polígono ID={poligono.id}, ID_POLIGONO={poligono.id_poligono}")
                except Exception as e:
                    print(f"Error al recuperar polígono {row_id}: {e}")
                    # Si no es un ID válido, continuar con el siguiente
                    continue
                
                # Generar ficha técnica PDF para este polígono
                pdf_buffer = generar_ficha_tecnica(poligono, f'polygon-{row_id}')
                if pdf_buffer:
                    zf.writestr(f'fichas_tecnicas/ficha_polygon-{row_id}.pdf', pdf_buffer.getvalue())
                
                # Generar shapefile para este polígono
                shapefile_buffer = generar_shapefile_individual(poligono, f'polygon-{row_id}')
                if shapefile_buffer:
                    zf.writestr(f'shapefiles/polygon-{row_id}.zip', shapefile_buffer.getvalue())
        
        # Regresar al inicio del archivo en memoria
        memory_file.seek(0)
        
        # Enviar el archivo ZIP como respuesta
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='paquete_completo.zip'
        )
    
    except Exception as e:
        print(f"Error al generar paquete completo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def generar_shapefile_individual(poligono, nombre_archivo):
    """Genera un archivo shapefile para un polígono individual"""
    try:
        # Crear un objeto de memoria para el archivo ZIP
        zip_buffer = io.BytesIO()
        
        # Crear un directorio temporal para los archivos del shapefile
        with tempfile.TemporaryDirectory() as tempdir:
            # Crear el writer de shapefile
            w = shapefile.Writer(os.path.join(tempdir, 'poligono'))
            
            # Definir campos de atributos
            w.field('ID_POLIG', 'C', 40)
            w.field('IF', 'C', 40)
            w.field('ID_CRED', 'C', 40)
            w.field('ID_PERS', 'C', 40)
            w.field('SUPERF', 'N', 10, 4)
            w.field('ESTADO', 'C', 40)
            w.field('MUNICIP', 'C', 40)
            w.field('AREA_HA', 'N', 10, 4)
            w.field('ESTATUS', 'C', 10)
            w.field('COMENT', 'C', 254)
            
            # Obtener coordenadas del polígono
            coords = []
            if poligono.coordenadas_corregidas:
                # Verificar qué separador usa: ' | ' o '|'
                if ' | ' in poligono.coordenadas_corregidas:
                    pares = poligono.coordenadas_corregidas.split(' | ')
                else:
                    pares = poligono.coordenadas_corregidas.split('|')
                
                for par in pares:
                    par = par.strip()
                    if par and ',' in par:
                        try:
                            partes = par.split(',')
                            lat = float(partes[0].strip())
                            lon = float(partes[1].strip())
                            coords.append([lon, lat])  # Shapefile usa [lon, lat]
                        except (ValueError, IndexError) as e:
                            print(f"Error al procesar coordenada {par}: {e}")
                            continue
                
                print(f"Coordenadas procesadas para shapefile: {coords}")
            
            # Si no hay suficientes coordenadas, usar un punto
            if len(coords) < 3:
                if len(coords) == 1:
                    # Crear un punto
                    w.point(coords[0][0], coords[0][1])
                    w.record(
                        poligono.id_poligono or '',
                        poligono.if_val or '',
                        poligono.id_credito or '',
                        poligono.id_persona or '',
                        poligono.superficie or 0,
                        corregir_codificacion(poligono.estado) or '',
                        corregir_codificacion(poligono.municipio) or '',
                        poligono.area_digitalizada or 0,
                        poligono.estatus or '',
                        poligono.comentarios or ''
                    )
                else:
                    # No hay coordenadas válidas
                    return None
            else:
                # Crear un polígono
                w.poly([coords])
                w.record(
                    poligono.id_poligono or '',
                    poligono.if_val or '',
                    poligono.id_credito or '',
                    poligono.id_persona or '',
                    poligono.superficie or 0,
                    corregir_codificacion(poligono.estado) or '',
                    corregir_codificacion(poligono.municipio) or '',
                    poligono.area_digitalizada or 0,
                    poligono.estatus or '',
                    poligono.comentarios or ''
                )
            
            # Guardar el shapefile
            w.close()
            
            # Crear archivo .prj para la proyección (WGS84)
            with open(os.path.join(tempdir, 'poligono.prj'), 'w') as prj:
                prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
            
            # Comprimir todos los archivos en un ZIP
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                for filename in os.listdir(tempdir):
                    filepath = os.path.join(tempdir, filename)
                    zf.write(filepath, filename)
        
        # Regresar al inicio del buffer
        zip_buffer.seek(0)
        return zip_buffer
    
    except Exception as e:
        print(f"Error al generar shapefile individual: {e}")
        import traceback
        traceback.print_exc()
        return None

def generar_ficha_tecnica(poligono, nombre_archivo):
    """Genera una ficha técnica en formato PDF para un polígono"""
    try:
        # Crear un buffer de memoria para el PDF
        buffer = io.BytesIO()
        
        # Crear el canvas
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Título
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1*inch, 10*inch, f"Ficha Técnica: {nombre_archivo}")
        
        # Detalles del polígono
        c.setFont("Helvetica", 12)
        
        y = 9*inch
        c.drawString(1*inch, y, f"ID Polígono: {poligono.id_poligono or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"IF: {poligono.if_val or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"ID Crédito: {poligono.id_credito or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"ID Persona: {poligono.id_persona or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Superficie Reportada: {poligono.superficie or 0} ha")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Área Digitalizada: {poligono.area_digitalizada or 0} ha")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Estado: {corregir_codificacion(poligono.estado) or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Municipio: {corregir_codificacion(poligono.municipio) or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Estatus: {poligono.estatus or 'N/A'}")
        
        # Comentarios
        y -= 0.5*inch
        c.drawString(1*inch, y, "Comentarios:")
        y -= 0.3*inch
        c.setFont("Helvetica", 10)
        comentarios = poligono.comentarios or "Sin comentarios"
        # Dividir comentarios en líneas si es muy largo
        import textwrap
        for line in textwrap.wrap(comentarios, width=70):
            c.drawString(1*inch, y, line)
            y -= 0.2*inch
        
        # Guardar el PDF
        c.save()
        
        # Regresar al inicio del buffer
        buffer.seek(0)
        return buffer
    
    except Exception as e:
        print(f"Error al generar ficha técnica: {e}")
        import traceback
        traceback.print_exc()
        return None

# Función para corregir la codificación de un texto
def corregir_codificacion(texto):
    if not texto:
        return texto
        
    try:
        # Si los nombres están en Latin-1 pero interpretados como UTF-8
        if isinstance(texto, str) and any(c in texto for c in ['Ã', 'Â']):
            return texto.encode('latin-1').decode('utf-8')
        return texto
    except Exception as e:
        print(f"Error al corregir codificación: {e}")
        return texto

if __name__ == '__main__':
    app.run(debug=True)