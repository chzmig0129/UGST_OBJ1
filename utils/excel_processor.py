import pandas as pd
import os
from datetime import datetime
from utils.database import db
from models.validacion_rapida import RegistroValidacionRapida

def procesar_excel_validacion_rapida(file_path):
    """
    Procesa un archivo Excel para la validación rápida
    
    Args:
        file_path: Ruta al archivo Excel
        
    Returns:
        dict: Resultado del procesamiento con información de filas procesadas y errores
    """
    try:
        # Validar que el archivo exista
        if not os.path.exists(file_path):
            return {
                "error": f"El archivo {file_path} no existe",
                "success": False
            }
        
        # Leer el archivo Excel
        df = pd.read_excel(file_path)
        
        # Validar que tenga las columnas necesarias
        columnas_requeridas = [
            'IF', 'ID.CREDITO', 'ESTATUS.CREDITO', 'FECHA.CREACIÓN', 
            'FECHA.AUTORIZACION', 'FECHA.VENCIMIENTO', 'ACCION', 'ID.PERSONA', 
            'ID_CARGA', 'ID_POLIGONO', 'SUPERFICIE', 'COORDENADAS', 'ESTATUS'
        ]
        
        # Normalizar los nombres de las columnas para facilitar la comparación
        columnas_actuales = [col.upper().replace(' ', '_') for col in df.columns]
        columnas_requeridas_norm = [col.upper().replace('.', '_').replace(' ', '_') for col in columnas_requeridas]
        
        # Verificar si están todas las columnas requeridas
        for col_req in columnas_requeridas_norm:
            if col_req not in columnas_actuales:
                # Buscar columnas similares (para ser flexibles con tildes, etc.)
                similar_found = False
                for col_act in columnas_actuales:
                    if col_req.replace('_', '') == col_act.replace('_', ''):
                        similar_found = True
                        break
                
                if not similar_found:
                    return {
                        "error": f"El archivo Excel no contiene la columna requerida: {col_req}",
                        "success": False
                    }
        
        # Mapeo de nombres de columnas
        column_mapping = {
            'IF': 'IF',
            'ID.CREDITO': 'ID_CREDITO',
            'ESTATUS.CREDITO': 'ESTATUS_CREDITO',
            'FECHA.CREACIÓN': 'FECHA_CREACION',
            'FECHA.AUTORIZACION': 'FECHA_AUTORIZACION',
            'FECHA.VENCIMIENTO': 'FECHA_VENCIMIENTO',
            'ACCION': 'ACCION',
            'ID.PERSONA': 'ID_PERSONA',
            'ID_CARGA': 'ID_CARGA',
            'ID_POLIGONO': 'ID_POLIGONO',
            'SUPERFICIE': 'SUPERFICIE',
            'COORDENADAS': 'COORDENADAS',
            'ESTATUS': 'ESTATUS'
        }
        
        # Procesar filas y guardarlas en la base de datos
        registros_procesados = 0
        errores = []
        
        for index, row in df.iterrows():
            try:
                # Crear diccionario con los datos de la fila
                datos = {}
                
                for col_orig, col_db in column_mapping.items():
                    # Buscar la columna en el dataframe (siendo flexible con nombres)
                    col_encontrada = None
                    for col_df in df.columns:
                        col_df_norm = col_df.upper().replace(' ', '_').replace('.', '_')
                        col_orig_norm = col_orig.upper().replace(' ', '_').replace('.', '_')
                        
                        if col_df_norm == col_orig_norm or col_df.replace(' ', '') == col_orig.replace('.', ''):
                            col_encontrada = col_df
                            break
                    
                    if col_encontrada:
                        datos[col_db] = row[col_encontrada]
                
                # Crear y guardar el registro en la base de datos
                registro = RegistroValidacionRapida.from_dict(datos)
                db.session.add(registro)
                registros_procesados += 1
                
            except Exception as e:
                errores.append(f"Error en la fila {index + 2}: {str(e)}")
        
        # Confirmar los cambios en la base de datos
        db.session.commit()
        
        return {
            "success": True,
            "registros_procesados": registros_procesados,
            "errores": errores,
            "total_filas": len(df)
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            "error": f"Error al procesar el archivo Excel: {str(e)}",
            "success": False
        }

def obtener_registros_validacion_rapida():
    """
    Obtiene todos los registros de validación rápida de la base de datos
    
    Returns:
        list: Lista de diccionarios con los datos de los registros
    """
    try:
        registros = RegistroValidacionRapida.query.all()
        return [registro.to_dict() for registro in registros]
    except Exception as e:
        print(f"Error al obtener registros: {str(e)}")
        return []

def obtener_registro_por_id(registro_id):
    """
    Obtiene un registro específico por su ID
    
    Args:
        registro_id: ID del registro a buscar
        
    Returns:
        dict: Datos del registro o None si no se encuentra
    """
    try:
        registro = RegistroValidacionRapida.query.get(registro_id)
        if registro:
            return registro.to_dict()
        return None
    except Exception as e:
        print(f"Error al obtener registro {registro_id}: {str(e)}")
        return None

def actualizar_registro(registro_id, datos):
    """
    Actualiza un registro existente
    
    Args:
        registro_id: ID del registro a actualizar
        datos: Diccionario con los nuevos datos
        
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        registro = RegistroValidacionRapida.query.get(registro_id)
        if not registro:
            return False
        
        # Actualizar solo los campos que pueden ser modificados por el usuario
        registro.nuevo_estatus = datos.get('NUEVO_ESTATUS', registro.nuevo_estatus)
        registro.descripcion = datos.get('DESCRIPCION', registro.descripcion)
        registro.traslape = datos.get('TRASLAPE', registro.traslape)
        registro.fo_con_xx = datos.get('FO_CON_XX', registro.fo_con_xx)
        
        # También permitir actualizar los campos básicos si es necesario
        if 'ESTATUS' in datos:
            registro.estatus = datos['ESTATUS']
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar registro {registro_id}: {str(e)}")
        return False

def eliminar_todos_registros():
    """
    Elimina todos los registros de validación rápida
    
    Returns:
        int: Número de registros eliminados
    """
    try:
        count = RegistroValidacionRapida.query.count()
        RegistroValidacionRapida.query.delete()
        db.session.commit()
        return count
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar registros: {str(e)}")
        return 0 