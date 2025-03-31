from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
import numpy as np
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB límite

# Variable global para almacenar los datos del Excel
excel_data = {
    'data': [],
    'columns': [],
    'filename': ''
}

# Asegurar que exista el directorio de uploads
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

            corrected_coords.append(f"{lat:.4f}, {lon:.4f}")
        except:
            continue

    return ' | '.join(corrected_coords)

def dms_a_decimal(coord):
    try:
        match_dir = re.search(r'([NSEW])$', coord.strip(), re.IGNORECASE)
        direccion = match_dir.group(1).upper() if match_dir else ''
        coord_num = re.sub(r'[^\d\.\-]', ' ', coord)
        parts = coord_num.strip().split()
        
        if len(parts) == 3:
            grados, minutos, segundos = map(float, parts)
        elif len(parts) == 2:
            grados, minutos = map(float, parts)
            segundos = 0.0
        elif len(parts) == 1:
            grados = float(parts[0])
            minutos = segundos = 0.0
        else:
            return np.nan
            
        decimal = grados + minutos/60 + segundos/3600
        if direccion in ['S', 'W']:
            decimal *= -1
        return round(decimal, 4)
    except:
        return np.nan

def es_dms(coord):
    if re.search('[°\'"]', coord):
        return True
    coord_num = re.sub(r'[^\d\.]', ' ', coord)
    parts = coord_num.strip().split()
    return len(parts) > 1

def procesar_coordenadas_dms(fila):
    if 'COORDENADAS' not in fila or pd.isna(fila['COORDENADAS']):
        return ''
    
    coordenadas = str(fila['COORDENADAS'])
    coordenadas = coordenadas.replace('\n', ' ').replace('\r', ' ').strip()
    coord_list = coordenadas.split('|')
    coord_list = [c.strip() for c in coord_list]

    coords_decimales = []
    
    for coord_pair in coord_list:
        coord_pair = coord_pair.strip()
        if not coord_pair:
            continue
            
        if ' ' in coord_pair and ',' not in coord_pair:
            parts = coord_pair.split()
            
            patterns = [
                r'([0-9\.]+[°][0-9\.]+[\'"][0-9\.]*[\"]*[NS])\s+([0-9\.]+[°][0-9\.]+[\'"][0-9\.]*[\"]*[WE])',
                r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s*[NS])\s+([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s*[WE])',
                r'([0-9\.]+\s+[0-9\.]+\s*[NS])\s+([0-9\.]+\s+[0-9\.]+\s*[WE])',
                r'([0-9\.]+\s*[NS])\s+([0-9\.]+\s*[WE])'
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
            if re.search(r'[0-9]', coord_pair):
                try:
                    coords_clean = re.sub(r'[^\d\.\-]', ' ', coord_pair)
                    nums = [float(x) for x in coords_clean.split() if x.strip()]
                    if len(nums) >= 2:
                        lat, lon = nums[0], nums[1]
                        if lon > 0 and lon > 90:
                            lon *= -1
                        coords_decimales.append(f"{lat:.4f}, {lon:.4f}")
                except:
                    pass
            continue

        lat_str = limpiar_coordenada(lat_str)
        lon_str = limpiar_coordenada(lon_str)

        try:
            if es_dms(lat_str):
                lat = dms_a_decimal(lat_str)
            else:
                lat_str_numeric = re.sub(r'[^\d\.\-]', '', lat_str)
                lat = float(lat_str_numeric)
                if 'S' in lat_str.upper():
                    lat *= -1
            if np.isnan(lat):
                continue
        except:
            continue

        try:
            if es_dms(lon_str):
                lon = dms_a_decimal(lon_str)
            else:
                lon_str_numeric = re.sub(r'[^\d\.\-]', '', lon_str)
                lon = float(lon_str_numeric)
                if 'W' in lon_str.upper():
                    lon *= -1
                elif lon > 0:
                    lon *= -1
            if np.isnan(lon):
                continue
        except:
            continue

        if not np.isnan(lat) and not np.isnan(lon):
            coords_decimales.append(f"{lat:.4f}, {lon:.4f}")

    return ' | '.join(coords_decimales)

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
        return render_template('validacion_poligonos.html', 
                            tab=tab, 
                            data=excel_data['data'],
                            columns=excel_data['columns'],
                            filename=excel_data['filename'])
    
    elif tab == 'editar':
        row_index = request.args.get('id', type=int)
        row_data = excel_data['data'][row_index] if row_index is not None and row_index < len(excel_data['data']) else None
        return render_template('validacion_poligonos.html', 
                            tab=tab, 
                            row_data=row_data,
                            row_index=row_index,
                            columns=excel_data['columns'])
    
    elif tab == 'generar':
        return render_template('validacion_poligonos.html', 
                            tab=tab,
                            data=excel_data['data'],
                            columns=excel_data['columns'])
    
    else:  # tab == 'cargar'
        columnas_ejemplo = [
            'ID_Poligono', 'Estado', 'Area_reportada', 'Area_digitalizada',
            'COORDENADAS', 'Municipio', 'ID_Credito_FIRA', 'ID_Persona',
            'Nombre_IF', 'Observaciones', 'Comentarios'
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
            filename = secure_filename(archivo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(filepath)
            
            df = pd.read_excel(filepath)
            
            if 'COORDENADAS' not in df.columns:
                flash('El archivo debe contener una columna llamada "COORDENADAS"', 'error')
                return redirect(url_for('validacion_poligonos'))
            
            # Procesar coordenadas
            df['COORDENADAS_DECIMALES'] = df.apply(procesar_coordenadas_dms, axis=1)
            df['COORDENADAS_DECIMALES_CORREGIDAS'] = df['COORDENADAS_DECIMALES'].apply(corregir_longitud)
            
            # Convertir a diccionario
            excel_data = {
                'data': df.replace({pd.NA: None}).to_dict('records'),
                'columns': list(df.columns),
                'filename': filename
            }
            
            flash('Archivo cargado y coordenadas procesadas correctamente', 'success')
            return redirect(url_for('validacion_poligonos', tab='lista'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('validacion_poligonos'))
    
    flash('Formato de archivo no permitido. Solo se aceptan .xlsx o .xls', 'error')
    return redirect(url_for('validacion_poligonos'))

@app.route('/actualizar-fila', methods=['POST'])
def actualizar_fila():
    global excel_data
    
    row_index = request.form.get('row_index', type=int)
    
    if row_index is None or row_index >= len(excel_data['data']):
        flash('Índice de fila inválido', 'error')
        return redirect(url_for('validacion_poligonos', tab='lista'))
    
    for col in excel_data['columns']:
        if col in request.form:
            excel_data['data'][row_index][col] = request.form[col]
    
    flash('Cambios guardados correctamente', 'success')
    return redirect(url_for('validacion_poligonos', tab='lista'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

if __name__ == '__main__':
    app.run(debug=True)