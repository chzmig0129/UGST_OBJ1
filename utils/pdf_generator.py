# Importaciones de PyMuPDF con múltiples alternativas
def import_pymupdf():
    global fitz
    
    print("\n=== INTENTANDO IMPORTAR PYMUPDF ===")
    
    # Intentar importar fitz directamente (confirmado que funciona según el diagnóstico)
    try:
        import fitz
        if hasattr(fitz, 'open'):
            print(f"✅ fitz importado correctamente con método 'open' disponible")
            print(f"   - Versión: {getattr(fitz, 'version', 'desconocida')}")
            return True
        else:
            print(f"❌ fitz importado pero sin método 'open'")
    except ImportError:
        print(f"❌ ImportError: No se pudo importar 'fitz'")
    
    # Si llegamos aquí, no pudimos importar fitz correctamente
    # Crear clase dummy como último recurso
    class DummyFitz:
        def __getattr__(self, name):
            error_msg = f"ADVERTENCIA: Se intentó acceder a 'fitz.{name}' pero PyMuPDF no está correctamente instalado"
            print(error_msg)
            if name == 'open':
                raise AttributeError("module 'fitz' has no attribute 'open'")
            return None
    
    # Asignar la clase dummy a fitz
    print("❌ Usando versión simulada de fitz como último recurso")
    fitz = DummyFitz()
    return False

# Intentar importar PyMuPDF
import_success = import_pymupdf()

# También usamos ReportLab como alternativa si PyMuPDF falla
import os
import tempfile
import io
import shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import traceback
import sys

# Función para garantizar que PyMuPDF esté correctamente importado
def garantizar_pymupdf():
    """Asegura que PyMuPDF esté correctamente importado y disponible"""
    global fitz
    
    # Verificar si fitz está correctamente importado y tiene el método open
    if 'fitz' in globals() and hasattr(fitz, 'open'):
        return True
    
    # Si fitz no está disponible, intentar importarlo de nuevo
    try:
        import fitz
        if hasattr(fitz, 'open'):
            return True
        else:
            print("❌ Error: fitz importado pero sin método 'open'")
            return False
    except ImportError:
        print("❌ Error: No se pudo importar fitz")
        return False

def verificar_instalacion_pymupdf():
    """Verifica la instalación de PyMuPDF"""
    try:
        # Verificar si fitz tiene los métodos necesarios
        print("\n=== DIAGNÓSTICO DE PYMUPDF ===")
        print(f"Tipo de 'fitz': {type(fitz)}")
        
        # Listar los atributos y métodos disponibles en fitz
        fitz_attrs = dir(fitz)
        print(f"Atributos y métodos de 'fitz': {', '.join(sorted([a for a in fitz_attrs if not a.startswith('_')]))}")
        
        # Verificación específica del método 'open'
        if hasattr(fitz, 'open'):
            print("✓ 'fitz.open' está disponible")
        else:
            print("✗ ERROR CRÍTICO: 'fitz.open' NO está disponible")
            
            # Intentar importar de otra manera
            try:
                import PyMuPDF
                print("Intentando importar como: import PyMuPDF")
                if hasattr(PyMuPDF, 'open'):
                    print("✓ 'PyMuPDF.open' está disponible - recomendado usar PyMuPDF directamente")
                    globals()['fitz'] = PyMuPDF
                    print("Se ha reasignado 'fitz' para usar 'PyMuPDF'")
                else:
                    print("✗ 'PyMuPDF.open' tampoco está disponible")
            except ImportError:
                print("No se pudo importar 'PyMuPDF' directamente")
        
        # Verificar versión
        try:
            print(f"PyMuPDF (fitz) version: {fitz.version}")
        except AttributeError:
            print("✗ No se pudo determinar la versión de PyMuPDF")
        
        # Si open no está disponible, mostrar las alternativas posibles
        if not hasattr(fitz, 'open'):
            print("\nPosibles soluciones:")
            print("1. Reinstalar PyMuPDF con: pip install --upgrade --force-reinstall PyMuPDF==1.22.5")
            print("2. Asegurarse de no tener conflictos con otros paquetes que usen el nombre 'fitz'")
            print("3. Verificar que la instalación de PyMuPDF está completa")
            return False
            
        # Crear un documento PDF simple para probar la biblioteca
        try:
            test_doc = fitz.open()  # Nuevo documento vacío
            page = test_doc.new_page()  # Nueva página
            
            try:
                page.insert_text((50, 50), "Prueba PyMuPDF")  # Insertar texto
            except AttributeError:
                # En algunas versiones antiguas, puede ser diferente
                page.insertText((50, 50), "Prueba PyMuPDF")
            
            # Guardar en un archivo temporal
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
            test_doc.save(temp_pdf)
            test_doc.close()
            
            # Verificar que el archivo se creó correctamente
            if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
                print(f"✓ Prueba de PyMuPDF exitosa: archivo creado con {os.path.getsize(temp_pdf)} bytes")
                os.unlink(temp_pdf)
                return True
            else:
                print("✗ Error: No se pudo crear un archivo PDF de prueba")
                return False
        except Exception as e:
            print(f"✗ Error al crear documento de prueba: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"✗ Error general al verificar PyMuPDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def obtener_datos_poligono(poligono, fecha_referencia=None, fecha_final=None):
    """Obtiene los datos del polígono en el formato requerido para la plantilla"""
    # Si no se proporcionan fechas, usar la fecha actual
    if not fecha_referencia:
        fecha_referencia = datetime.now().strftime("%d de %B de %Y")
    else:
        # Convertir la fecha del formato YYYY-MM-DD al formato deseado
        fecha_obj = datetime.strptime(fecha_referencia, "%Y-%m-%d")
        fecha_referencia = fecha_obj.strftime("%d de %B de %Y")
        
    if not fecha_final:
        fecha_final = datetime.now().strftime("%d de %B de %Y")
    else:
        # Convertir la fecha del formato YYYY-MM-DD al formato deseado
        fecha_obj = datetime.strptime(fecha_final, "%Y-%m-%d")
        fecha_final = fecha_obj.strftime("%d de %B de %Y")
    
    # Printing values from polygon for debugging
    print(f"DEBUG - Datos del polígono:")
    print(f"  ID: {poligono.id}")
    print(f"  ID_POLIGONO: {poligono.id_poligono}")
    print(f"  IF: {poligono.if_val}")
    print(f"  ID_CREDITO: {poligono.id_credito}")
    print(f"  ID_PERSONA: {poligono.id_persona}")
    print(f"  SUPERFICIE: {poligono.superficie}")
    print(f"  ESTADO: {poligono.estado}")
    print(f"  MUNICIPIO: {poligono.municipio}")
    print(f"  AREA_DIGITALIZADA: {poligono.area_digitalizada}")
    print(f"  COMENTARIOS: {poligono.comentarios}")
    
    # Mapping based on the template from the image
    field_mapping = {
        # Patrones de texto encontrados en el template Plantilla_2.pdf
        "BBVA MEXICO": str(poligono.if_val or 'N/A'),
        "FINANCIERA BAJIO": str(poligono.if_val or 'N/A'),
        "BAJIO": str(poligono.if_val or 'N/A'),
        
        "Colima": str(poligono.estado or 'N/A'),
        "COAHUILA": str(poligono.estado or 'N/A'),
        "COAHUILA DE ZARAGOZA": str(poligono.estado or 'N/A'),
        
        "8-750-00020347-2": str(poligono.id_poligono or 'N/A'),
        "7-711-00108534-2": str(poligono.id_poligono or 'N/A'),
        
        "Tecomán": str(poligono.municipio or 'N/A'),
        "SIERRA MOJADA": str(poligono.municipio or 'N/A'),
        
        "2428165": str(poligono.id_credito or 'N/A'),
        "2609194": str(poligono.id_credito or 'N/A'),
        
        "2077178": str(poligono.id_persona or 'N/A'),
        "14217744": str(poligono.id_persona or 'N/A'),
        
        "7.0": f"{poligono.superficie or 0}",
        "7.0 ha": f"{poligono.superficie or 0} ha",
        "106.5": f"{poligono.superficie or 0}",
        
        "2.22": f"{poligono.area_digitalizada or 0}",
        "2.22 ha": f"{poligono.area_digitalizada or 0} ha",
        "91.5": f"{poligono.area_digitalizada or 0}",
        
        "Sin comentarios": str(poligono.comentarios or 'Sin comentarios'),
        "NO CUMPLE CON LA SUPERFICIE": str(poligono.comentarios or 'Sin comentarios'),
        
        "19/04/2025": fecha_referencia,
        "10 de julio de 2024": fecha_referencia,
        "08 de septiembre de 2024": fecha_final
    }
    
    print(f"DEBUG - Mapping creado con {len(field_mapping)} patrones")
    return field_mapping

def analizar_plantilla_pdf(plantilla_pdf):
    """Analiza el contenido de la plantilla PDF e imprime información detallada"""
    try:
        print(f"\n=== ANALIZANDO PLANTILLA: {plantilla_pdf} ===")
        if not os.path.exists(plantilla_pdf):
            print(f"ERROR: El archivo no existe: {plantilla_pdf}")
            return False
            
        try:
            # Verificar permisos de acceso
            with open(plantilla_pdf, 'rb') as f:
                _ = f.read(10)
                print("Verificación de acceso: OK - Se puede leer el archivo")
        except Exception as e:
            print(f"ERROR: No se puede abrir el archivo: {e}")
            return False
            
        # Abrir el PDF
        try:
            pdf_documento = fitz.open(plantilla_pdf)
            print(f"PDF abierto correctamente: {len(pdf_documento)} páginas")
            
            # Para cada página
            for page_num in range(len(pdf_documento)):
                page = pdf_documento[page_num]
                print(f"\nINFORMACIÓN DE PÁGINA {page_num+1}:")
                
                # Extraer texto
                texto = page.get_text()
                print(f"- Longitud del texto: {len(texto)} caracteres")
                
                # Mostrar primeras líneas del texto
                lineas = texto.split('\n')
                print("- Primeras 10 líneas:")
                for i, linea in enumerate(lineas[:10]):
                    if linea.strip():
                        print(f"  {i+1}: {linea[:50]}")
                
                # Mostrar todas las imágenes
                images = page.get_images()
                print(f"- Imágenes: {len(images)}")
                
                # Extraer bloques de texto
                blocks = page.get_text("blocks")
                print(f"- Bloques de texto: {len(blocks)}")
                
                # Imprimir algunos bloques representativos
                if blocks:
                    print("- Muestra de bloques:")
                    for i, b in enumerate(blocks[:5]):
                        print(f"  Bloque {i+1}: {b[4][:30]}...")
            
            # Extraer información del documento
            meta = pdf_documento.metadata
            print("\nMETADATOS DEL PDF:")
            for key, value in meta.items():
                if value:
                    print(f"- {key}: {value}")
            
            pdf_documento.close()
            print("=== ANÁLISIS COMPLETADO ===\n")
            return True
            
        except Exception as e:
            print(f"ERROR al analizar PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        return False

# Guardar constantes para medidas de imagen para garantizar consistencia en todas las fichas
# Estos valores se usarán en todos los lugares donde se inserta una imagen
IMAGEN_ANCHO_ESTANDAR = 700  # Ancho en píxeles
IMAGEN_ALTO_ESTANDAR = 350   # Alto en píxeles
IMAGEN_POSICION_VERTICAL = 0.20  # Como porcentaje de la altura de la página
IMAGEN_OFFSET_VERTICAL = 5 * (72/96)  # 5 píxeles convertidos a puntos

def estandarizar_imagen_para_pdf(image_path):
    """
    Procesa la imagen para garantizar un tamaño estándar en todas las fichas técnicas
    """
    try:
        # Si la imagen no existe, devolver None
        if not os.path.exists(image_path):
            print(f"La imagen no existe: {image_path}")
            return None
            
        # Verificar la imagen y estandarizar su tamaño si es necesario
        from PIL import Image
        img = Image.open(image_path)
        
        # Verificar dimensiones
        width, height = img.size
        print(f"Dimensiones originales de la imagen: {width}x{height}")
        
        # Usar los valores de las constantes globales para garantizar consistencia
        print(f"Redimensionando TODAS las imágenes a tamaño estándar ({IMAGEN_ANCHO_ESTANDAR}x{IMAGEN_ALTO_ESTANDAR})")
        
        # Redimensionar SIEMPRE para garantizar uniformidad
        img_resized = img.resize((IMAGEN_ANCHO_ESTANDAR, IMAGEN_ALTO_ESTANDAR), Image.LANCZOS)
        
        # Guardar imagen procesada en archivo temporal
        temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
        img_resized.save(temp_img_path, format='PNG')
        print(f"Imagen estandarizada guardada en: {temp_img_path}")
        return temp_img_path
        
    except Exception as e:
        print(f"Error al estandarizar imagen: {e}")
        traceback.print_exc()
        return image_path  # Devolver la original en caso de error

def generar_ficha_tecnica_desde_plantilla(poligono, image_path, fecha_referencia=None, fecha_final=None):
    """Genera una ficha técnica en formato PDF para un polígono utilizando la plantilla"""
    try:
        print("\n============= INICIANDO GENERACIÓN CON PLANTILLA =============")
        
        # Verificar que PyMuPDF esté disponible
        if not garantizar_pymupdf():
            print("ERROR: PyMuPDF no está correctamente instalado o configurado")
            print("Intentando generar PDF con método simple...")
            return generar_ficha_tecnica_simple(poligono, image_path)
            
        import os
        import tempfile
        
        # SIEMPRE estandarizar la imagen para garantizar tamaño uniforme entre fichas
        processed_image_path = estandarizar_imagen_para_pdf(image_path)
        print(f"Se utilizará la imagen estandarizada: {processed_image_path}")
        
        # Obtener ruta de la plantilla (puede ser ajustada según convenga)
        plantilla_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'templates')
        plantilla_pdf = os.path.join(plantilla_dir, 'Plantilla_2.pdf')
        
        if not os.path.exists(plantilla_pdf):
            print(f"ADVERTENCIA: No se encuentra la plantilla principal: {plantilla_pdf}")
            # Intentar rutas alternativas
            alternativas = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'plantilla', 'Plantilla_2.pdf'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'Plantilla_2.pdf'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Plantilla_2.pdf'),
                'Plantilla_2.pdf'
            ]
            for alt in alternativas:
                if os.path.exists(alt):
                    plantilla_pdf = alt
                    print(f"Usando plantilla alternativa: {plantilla_pdf}")
                    break
            
            # Verificar si se encontró alguna plantilla
            if os.path.exists(plantilla_pdf):
                print(f"Plantilla encontrada en: {os.path.abspath(plantilla_pdf)}")
                # Verificar si el archivo es accesible
                try:
                    with open(plantilla_pdf, 'rb') as f:
                        _ = f.read(10)
                    print(f"Archivo de plantilla accesible: {plantilla_pdf}")
                except Exception as e:
                    print(f"ERROR: No se puede acceder a la plantilla: {str(e)}")
        
        # Verificar si se encontró alguna plantilla
        if not os.path.exists(plantilla_pdf):
            print("ERROR: No se encontró ninguna plantilla válida")
            print("Intentando generar PDF con método simple...")
            return generar_ficha_tecnica_simple(poligono, processed_image_path)
        
        # Crear un nombre de archivo temporal para la salida
        output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        print(f"Archivo de salida temporal: {output_pdf}")
        
        # Obtener datos para los campos
        field_mapping = obtener_datos_poligono(poligono, fecha_referencia, fecha_final)
        id_poligono = str(poligono.id_poligono or 'N/A')
        
        # Realizar el reemplazo de contenido usando PyMuPDF
        print("Usando PyMuPDF para generar el PDF con la plantilla")
        resultado = reemplazar_contenido_pdf(plantilla_pdf, output_pdf, field_mapping, id_poligono, processed_image_path)
        
        if resultado:
            # Agregar líneas para firmas
            try:
                agregar_lineas_firmas(output_pdf)
                print("Líneas de firma agregadas correctamente")
            except Exception as e:
                print(f"Error al agregar líneas de firma: {e}")
                # Continuar con el archivo generado sin líneas de firma
            
            # Leer el archivo para devolverlo como buffer
            with open(output_pdf, 'rb') as f:
                buffer = io.BytesIO(f.read())
            
            # Eliminar el archivo temporal
            try:
                os.unlink(output_pdf)
                # Importante: Siempre eliminar la imagen procesada si es diferente de la original
                if processed_image_path != image_path and os.path.exists(processed_image_path):
                    os.unlink(processed_image_path)
                    print(f"Imagen temporal eliminada: {processed_image_path}")
            except Exception as e:
                print(f"Error al eliminar archivos temporales: {e}")
            
            print("PDF generado correctamente con plantilla")
            print("============= FIN GENERACIÓN CON PLANTILLA (ÉXITO) =============\n")
            return buffer
        else:
            print("ERROR: Fallo en la generación del PDF con plantilla")
            print("Intentando método alternativo...")
            # Si falló, usar método alternativo
            return generar_ficha_tecnica_simple(poligono, processed_image_path)
        
    except Exception as e:
        print(f"ERROR CRÍTICO al generar ficha técnica desde plantilla: {e}")
        print(f"Detalles del polígono: ID={getattr(poligono, 'id', 'N/A')}, ID_POLIGONO={getattr(poligono, 'id_poligono', 'N/A')}")
        print(f"Ruta de la imagen: {image_path}")
        import traceback
        traceback.print_exc()
        print("============= FIN GENERACIÓN CON PLANTILLA (ERROR) =============\n")
        # Si ocurre cualquier error, intentar el método simple
        try:
            print("Intentando generar PDF con método simple debido a error en el método principal...")
            return generar_ficha_tecnica_simple(poligono, processed_image_path)
        except Exception as simple_error:
            print(f"Error en método simple: {simple_error}")
            print("Intentando método ultra básico...")
            return generar_ficha_tecnica_fallback(poligono, processed_image_path)

def reemplazar_contenido_pdf(plantilla_pdf, output_pdf, field_mapping, id_poligono, image_path):
    """Reemplaza el contenido de la plantilla PDF con los datos proporcionados"""
    try:
        # Verificar que fitz esté disponible
        if not garantizar_pymupdf():
            raise ImportError("No se pudo importar PyMuPDF correctamente")
        
        print(f"Abriendo plantilla PDF: {plantilla_pdf}")
        import os
        template_name = os.path.basename(plantilla_pdf)
        print(f"=== USANDO PLANTILLA: {template_name} ===")
        
        # Intentar abrir el documento
        pdf_documento = fitz.open(plantilla_pdf)
        print(f"Plantilla PDF abierta: {len(pdf_documento)} páginas")
        comentarios_reemplazados = False
        estado_reemplazado = False
        
        # Verificar dimensiones para depuración
        first_page = pdf_documento[0]
        page_width = first_page.rect.width
        page_height = first_page.rect.height
        print(f"Dimensiones de la página: {page_width} x {page_height}")

        for page_num in range(len(pdf_documento)):
            page = pdf_documento[page_num]
            print(f"Procesando página {page_num+1}")
            
            # Extraer texto para depuración
            page_text = page.get_text()
            print(f"=== CONTENIDO DE LA PÁGINA {page_num+1} ===")
            print(page_text[:500])  # Solo mostrar los primeros 500 caracteres
            print("...")

            # Eliminar la línea azul con un rectángulo más grande
            rect_linea = fitz.Rect(0, 850, 595, 850)
            page.draw_rect(rect_linea, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Contar reemplazos realizados para depuración
            reemplazos_realizados = 0

            # Manejar caso especial para Estado (buscar y reemplazar "DE ZARAGOZA" completo)
            if not estado_reemplazado:
                print("Buscando texto completo de Estado para reemplazar...")
                # Buscar términos completos como "COAHUILA DE ZARAGOZA"
                terminos_estado = ["COAHUILA DE ZARAGOZA", "DE ZARAGOZA"]
                for termino in terminos_estado:
                    areas = page.search_for(termino)
                    if areas:
                        print(f"Encontrado término de estado: '{termino}' - {len(areas)} ocurrencias")
                        for area in areas:
                            # Eliminar completamente el texto antiguo
                            page.add_redact_annot(area, fill=(1, 1, 1))
                            page.apply_redactions()
                            # Si es el término completo, insertar el nuevo valor
                            if termino == "COAHUILA DE ZARAGOZA":
                                x0, y0, x1, y1 = area
                                y0 += 9
                                nuevo_estado = str(field_mapping.get("Colima") or field_mapping.get("COAHUILA") or "N/A")
                                page.insert_text((x0, y0), nuevo_estado, fontsize=9, color=(0, 0, 0))
                                print(f"Reemplazado estado completo: '{termino}' -> '{nuevo_estado}'")
                        estado_reemplazado = True
                        reemplazos_realizados += len(areas)

            for original_text, new_value in field_mapping.items():
                # Omitir campos de estado ya procesados
                if estado_reemplazado and (original_text == "Colima" or original_text == "COAHUILA" or original_text == "COAHUILA DE ZARAGOZA"):
                    continue
                    
                if original_text == "NO CUMPLE CON LA SUPERFICIE" and comentarios_reemplazados:
                    continue

                areas = page.search_for(original_text)
                if len(areas) > 0:
                    reemplazos_realizados += len(areas)
                    print(f"Texto encontrado: '{original_text}' -> '{new_value}' - {len(areas)} ocurrencias")
                
                if original_text == "NO CUMPLE CON LA SUPERFICIE" or original_text == "Sin comentarios":
                    if areas:
                        area = areas[0]
                        x0, y0, x1, y1 = area
                        y0 += 9
                        page.add_redact_annot(area, fill=(1, 1, 1))
                        page.apply_redactions()
                        page.insert_text((x0, y0), str(new_value), fontsize=9, color=(0, 0, 0))
                        comentarios_reemplazados = True
                else:
                    for area in areas:
                        page.add_redact_annot(area, fill=(1, 1, 1))
                        page.apply_redactions()
                        x0, y0, x1, y1 = area
                        y0 += 9
                        page.insert_text((x0, y0), str(new_value), fontsize=9, color=(0, 0, 0))

            print(f"Total de reemplazos realizados en la página {page_num+1}: {reemplazos_realizados}")
            if reemplazos_realizados == 0:
                print("ADVERTENCIA: No se encontraron textos para reemplazar en esta página")
                # Intentar método alternativo - añadir nuevos bloques de texto en posiciones clave
                try:
                    print("Intentando método alternativo de añadir texto en posiciones clave...")
                    # Añadir ID polígono en la parte superior
                    page.insert_text((250, 150), f"ID: {id_poligono}", fontsize=12, color=(0, 0, 0))
                    # Añadir IF
                    page.insert_text((100, 180), f"IF: {field_mapping.get('BBVA MEXICO')}", fontsize=10, color=(0, 0, 0))
                    # Añadir datos adicionales
                    page.insert_text((100, 200), f"Estado: {field_mapping.get('Colima')}", fontsize=10, color=(0, 0, 0))
                    page.insert_text((300, 200), f"Municipio: {field_mapping.get('Tecomán')}", fontsize=10, color=(0, 0, 0))
                    page.insert_text((100, 220), f"Superficie: {field_mapping.get('7.0 ha')}", fontsize=10, color=(0, 0, 0))
                    page.insert_text((300, 220), f"Área Dig.: {field_mapping.get('2.22 ha')}", fontsize=10, color=(0, 0, 0))
                    print("Texto añadido con método alternativo")
                except Exception as alt_error:
                    print(f"Error en método alternativo: {alt_error}")

            # Sección para manejar la imagen de manera segura
            try:
                # Reemplazo de la imagen si existe el archivo
                if os.path.exists(image_path):
                    print(f"Insertando imagen en el PDF: {image_path}")
                    
                    # Usar las constantes globales para dimensiones y posición
                    image_width = page_width * 0.8
                    image_height = page_height * 0.4
                    left = (page_width - image_width) / 2
                    
                    # Usar los valores constantes para la posición vertical
                    top = page_height * IMAGEN_POSICION_VERTICAL + IMAGEN_OFFSET_VERTICAL
                    right = left + image_width
                    bottom = top + image_height
                    
                    # Crear el rectángulo con medidas absolutamente consistentes
                    IMAGE_RECT = fitz.Rect(left, top, right, bottom)
                    
                    print(f"Coordenadas estandarizadas para imagen: {IMAGE_RECT}")
                    
                    try:
                        # Verificar que la imagen ya haya sido procesada al tamaño estándar
                        from PIL import Image
                        img = Image.open(image_path)
                        img_width, img_height = img.size
                        print(f"Verificando dimensiones de imagen: {img_width}x{img_height}")
                        
                        # Verificar que las dimensiones sean las esperadas
                        if img_width != IMAGEN_ANCHO_ESTANDAR or img_height != IMAGEN_ALTO_ESTANDAR:
                            print(f"ADVERTENCIA: La imagen no tiene el tamaño estándar esperado ({IMAGEN_ANCHO_ESTANDAR}x{IMAGEN_ALTO_ESTANDAR})")
                        
                        # Insertar la imagen - IMPORTANTE: NO usar keep_proportion para mantener tamaño consistente
                        # El uso de keep_proportion puede causar que las imágenes se muestren de tamaños diferentes
                        page.insert_image(IMAGE_RECT, filename=image_path)
                        print("Imagen insertada correctamente con tamaño estándar")
                    except Exception as img_error:
                        print(f"Error al verificar/insertar imagen: {img_error}")
                        import traceback
                        traceback.print_exc()
                        
                        # Intentar generar y usar una imagen alternativa
                        print("Generando imagen alternativa...")
                        placeholder_img_path = None # Inicializar
                        try:
                            # Crear imagen de texto simple - usar dimensiones estándar
                            placeholder_img = Image.new('RGB', (IMAGEN_ANCHO_ESTANDAR, IMAGEN_ALTO_ESTANDAR), color=(240, 240, 240))
                            d = ImageDraw.Draw(placeholder_img)
                            texto_error = f"Error al cargar imagen original\nID Polígono: {id_poligono}"
                            d.text((IMAGEN_ANCHO_ESTANDAR//2, IMAGEN_ALTO_ESTANDAR//2), texto_error, fill=(100, 100, 100), anchor="mm", align="center")
                            
                            # Guardar en un archivo temporal
                            placeholder_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            placeholder_img.save(placeholder_img_path)
                            
                            # Insertar esta imagen alternativa usando las mismas coordenadas exactas
                            page.insert_image(IMAGE_RECT, filename=placeholder_img_path)
                            print("Imagen alternativa insertada correctamente")
                        except Exception as alt_img_error:
                            print(f"No se pudo insertar imagen alternativa: {alt_img_error}")
                        finally:
                            # Limpiar el archivo temporal
                            try:
                                if placeholder_img_path and os.path.exists(placeholder_img_path):
                                    os.unlink(placeholder_img_path)
                            except Exception as e:
                                print(f"Error al eliminar archivo temporal de imagen alternativa: {e}")
                else:
                    print(f"ADVERTENCIA: No se pudo insertar la imagen porque no existe: {image_path}")
                    
                    # Crear una imagen de marcador de posición
                    placeholder_img_path = None # Inicializar
                    try:
                        print("Creando imagen de marcador de posición...")
                        from PIL import Image, ImageDraw
                        
                        # Crear una imagen en blanco con las dimensiones estándar
                        placeholder_img = Image.new('RGB', (IMAGEN_ANCHO_ESTANDAR, IMAGEN_ALTO_ESTANDAR), color=(240, 240, 240))
                        d = ImageDraw.Draw(placeholder_img)
                        
                        # Dibujar texto informativo
                        text = f"No hay imagen disponible\nID Polígono: {id_poligono}"
                        d.text((IMAGEN_ANCHO_ESTANDAR//2, IMAGEN_ALTO_ESTANDAR//2), text, fill=(100, 100, 100), anchor="mm", align="center")
                        
                        # Guardar en un archivo temporal
                        placeholder_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                        placeholder_img.save(placeholder_img_path)
                        
                        # Insertar imagen - NO usar keep_proportion para mantener tamaño
                        page.insert_image(IMAGE_RECT, filename=placeholder_img_path)
                        
                    except Exception as e:
                        print(f"No se pudo crear/insertar imagen de marcador de posición: {e}")
                    finally:
                        # Limpiar el archivo temporal
                        try:
                            if placeholder_img_path and os.path.exists(placeholder_img_path):
                                os.unlink(placeholder_img_path)
                        except Exception as e:
                            print(f"Error al eliminar archivo temporal de placeholder: {e}")
                            
            except Exception as img_section_error:
                print(f"Error general en la sección de manejo de imágenes: {img_section_error}")
                import traceback
                traceback.print_exc()
                print("Continuando con la generación del PDF sin imagen...")

        print(f"Guardando PDF modificado en: {output_pdf}")
        temp_output_pdf = output_pdf.replace(".pdf", "_temp.pdf")
        
        try:
            pdf_documento.save(temp_output_pdf)
            pdf_documento.close()
        except Exception as save_error:
            print(f"ERROR al guardar PDF en {temp_output_pdf}: {save_error}")
            pdf_documento.close() # Asegurarse de cerrar el documento
            raise # Re-lanzar el error para que sea capturado afuera
        
        # Verificar si el archivo de salida temporal existe y tiene contenido
        if os.path.exists(temp_output_pdf) and os.path.getsize(temp_output_pdf) > 0:
            import shutil
            try:
                shutil.move(temp_output_pdf, output_pdf)
                print(f"PDF guardado exitosamente en: {output_pdf} ({os.path.getsize(output_pdf)} bytes)")
                return True # Indicar éxito
            except Exception as move_error:
                print(f"ERROR al mover {temp_output_pdf} a {output_pdf}: {move_error}")
                # Intentar leer el archivo temporal como último recurso
                try:
                    with open(temp_output_pdf, 'rb') as f_temp:
                        content = f_temp.read()
                    with open(output_pdf, 'wb') as f_out:
                        f_out.write(content)
                    print("Copia manual realizada como fallback.")
                    return True
                except Exception as fallback_copy_error:
                    print(f"Error en copia manual: {fallback_copy_error}")
                    return False # Indicar fallo
        else:
            print(f"ERROR: No se generó un archivo PDF válido o está vacío en {temp_output_pdf}")
            return False # Indicar fallo

    except Exception as e:
        print(f"ERROR CRÍTICO al generar PDF para el ID Polígono '{id_poligono}': {e}")
        print(f"Ruta de la plantilla: {plantilla_pdf}")
        print(f"Ruta de salida: {output_pdf}")
        print(f"Ruta de la imagen: {image_path}")
        print(f"Field mapping: {field_mapping}")
        import traceback
        traceback.print_exc()
        raise # Re-lanzar para que la función llamadora sepa que falló

def agregar_lineas_firmas(output_pdf):
    """Agrega líneas para firmas en la última página del PDF"""
    try:
        pdf_documento = fitz.open(output_pdf)
        ultima_pagina = pdf_documento[-1]

        # Coordenadas ajustadas para líneas más cortas
        linea_firma1 = fitz.Rect(50, 685, 270, 685)  # Primera firma (izquierda)
        linea_firma2 = fitz.Rect(340, 685, 560, 685)  # Segunda firma (derecha)

        # Dibujar las líneas con grosor ajustado
        ultima_pagina.draw_line(linea_firma1.tl, linea_firma1.br, width=0.5, color=(0, 0, 0))
        ultima_pagina.draw_line(linea_firma2.tl, linea_firma2.br, width=0.5, color=(0, 0, 0))

        # Eliminar línea azul del pie de página con un rectángulo más grande
        rect_linea = fitz.Rect(0, 800, 50, 845)
        ultima_pagina.draw_rect(rect_linea, color=(1, 1, 1), fill=(1, 1, 1))

        temp_output_pdf = output_pdf.replace(".pdf", "_temp.pdf")
        pdf_documento.save(temp_output_pdf)
        pdf_documento.close()
        shutil.move(temp_output_pdf, output_pdf)

    except Exception as e:
        print(f"Error al agregar líneas de firma: {e}")
        raise

def generar_ficha_tecnica_fallback(poligono, image_path):
    """Genera una ficha técnica utilizando ReportLab como fallback si PyMuPDF falla"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        
        print("Utilizando método fallback con ReportLab para generar PDF")
        
        # Crear un buffer de memoria para el PDF
        buffer = io.BytesIO()
        
        # Crear el canvas
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, 10*inch, "FICHA TÉCNICA (VERSIÓN ALTERNATIVA)")
        
        # Datos del polígono
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, 9*inch, "Datos del Polígono:")
        
        # Contenido
        c.setFont("Helvetica", 10)
        y_pos = 8.5*inch
        
        # Campos a mostrar
        fields = [
            ("ID Polígono:", poligono.id_poligono or "N/A"),
            ("IF:", poligono.if_val or "N/A"),
            ("ID Crédito:", poligono.id_credito or "N/A"),
            ("ID Persona:", poligono.id_persona or "N/A"),
            ("Superficie (reportada):", f"{poligono.superficie or 0} ha"),
            ("Superficie (digitalizada):", f"{poligono.area_digitalizada or 0} ha"),
            ("Estado:", poligono.estado or "N/A"),
            ("Municipio:", poligono.municipio or "N/A"),
            ("Comentarios:", poligono.comentarios or "Sin comentarios")
        ]
        
        # Dibujar campos
        for label, value in fields:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1*inch, y_pos, label)
            c.setFont("Helvetica", 10)
            c.drawString(2.5*inch, y_pos, str(value))
            y_pos -= 0.3*inch
        
        # Imagen
        try:
            if os.path.exists(image_path):
                # Posición para la imagen
                img_x = 1*inch
                img_y = 3*inch
                img_width = 6*inch
                img_height = 3*inch
                
                # Dibujar un recuadro para la imagen
                c.rect(img_x, img_y, img_width, img_height)
                
                # Insertar la imagen
                c.drawImage(image_path, img_x, img_y, width=img_width, height=img_height, preserveAspectRatio=True)
            else:
                c.setFont("Helvetica-Oblique", 12)
                c.drawCentredString(width/2, 4.5*inch, "Imagen no disponible")
        except Exception as e:
            print(f"Error al insertar imagen en método fallback: {e}")
            c.setFont("Helvetica-Oblique", 12)
            c.drawCentredString(width/2, 4.5*inch, "Error al cargar la imagen")
        
        # Pie de página
        c.setFont("Helvetica", 8)
        today = datetime.now().strftime("%d/%m/%Y")
        c.drawString(1*inch, 1*inch, f"Fecha de generación: {today}")
        c.drawString(1*inch, 0.8*inch, f"Este documento es una versión alternativa generada debido a un error en el proceso principal.")
        
        # Guardar el PDF
        c.save()
        
        # Regresar al inicio del buffer
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error al generar ficha técnica fallback: {e}")
        import traceback
        traceback.print_exc()
        return None

def generar_ficha_tecnica_simple(poligono, image_path):
    """Función simple para generar PDFs que minimiza cualquier posible error"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    
    print("Generando PDF con método ultra-simple (ReportLab directo)")
    
    try:
        # Crear un buffer para el PDF
        buffer = io.BytesIO()
        
        # Crear el canvas
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, 10*inch, "FICHA TÉCNICA")
        
        # Datos del polígono
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, 9*inch, "Datos del Polígono:")
        
        # Contenido
        c.setFont("Helvetica", 10)
        y_pos = 8.5*inch
        
        # Campos a mostrar
        fields = [
            ("ID Polígono:", poligono.id_poligono or "N/A"),
            ("IF:", poligono.if_val or "N/A"),
            ("ID Crédito:", poligono.id_credito or "N/A"),
            ("ID Persona:", poligono.id_persona or "N/A"),
            ("Superficie (reportada):", f"{poligono.superficie or 0} ha"),
            ("Superficie (digitalizada):", f"{poligono.area_digitalizada or 0} ha"),
            ("Estado:", poligono.estado or "N/A"),
            ("Municipio:", poligono.municipio or "N/A"),
            ("Comentarios:", poligono.comentarios or "Sin comentarios")
        ]
        
        # Dibujar campos
        for label, value in fields:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1*inch, y_pos, label)
            c.setFont("Helvetica", 10)
            c.drawString(2.5*inch, y_pos, str(value))
            y_pos -= 0.3*inch
        
        # Verificar existencia y accesibilidad de la imagen
        imagen_ok = False
        if image_path and os.path.exists(image_path):
            try:
                # Intentar abrir la imagen
                from PIL import Image
                img = Image.open(image_path)
                img.verify()  # Verificar que la imagen es válida
                imagen_ok = True
            except Exception as e:
                print(f"Error al verificar imagen {image_path}: {e}")
        
        # Insertar imagen si es posible
        if imagen_ok:
            try:
                # Posición para la imagen
                img_x = 1*inch
                img_y = 3*inch
                img_width = 6*inch
                img_height = 3*inch
                
                # Dibujar un recuadro para la imagen
                c.rect(img_x, img_y, img_width, img_height)
                
                # Insertar la imagen
                c.drawImage(image_path, img_x, img_y, width=img_width, height=img_height, preserveAspectRatio=True)
            except Exception as e:
                print(f"Error al insertar imagen: {e}")
                c.setFont("Helvetica-Oblique", 12)
                c.drawCentredString(width/2, 4.5*inch, "Error al cargar la imagen")
        else:
            c.setFont("Helvetica-Oblique", 12)
            c.drawCentredString(width/2, 4.5*inch, "Imagen no disponible")
            
            # Dibujar un recuadro para indicar dónde iría la imagen
            c.rect(1*inch, 3*inch, 6*inch, 3*inch)
        
        # Pie de página
        c.setFont("Helvetica", 9)
        c.line(1*inch, 2*inch, width-1*inch, 2*inch)
        
        today = datetime.now().strftime("%d/%m/%Y")
        c.drawString(1*inch, 1.5*inch, f"Fecha de generación: {today}")
        
        # Firmas
        c.drawString(1.5*inch, 1*inch, "José Renato Navarrete Pérez")
        c.drawString(5*inch, 1*inch, "Oswaldo Rahmses Castro Martínez")
        c.line(1*inch, 1.1*inch, 3*inch, 1.1*inch)
        c.line(4.5*inch, 1.1*inch, 6.5*inch, 1.1*inch)
        
        # Guardar el PDF
        c.save()
        
        # Regresar al inicio del buffer
        buffer.seek(0)
        print(f"PDF generado correctamente con método simple ({len(buffer.getvalue())} bytes)")
        return buffer
    except Exception as e:
        print(f"Error en generación simple: {e}")
        import traceback
        traceback.print_exc()
        
        # Método ultra-básico como último recurso
        try:
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            
            # Contenido mínimo
            c.drawString(100, 700, f"ID Polígono: {poligono.id_poligono or 'N/A'}")
            c.drawString(100, 680, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
            c.drawString(100, 660, "Documento mínimo de emergencia - Generado ante error")
            
            c.save()
            buffer.seek(0)
            print("PDF mínimo generado como último recurso")
            return buffer
        except Exception as last_error:
            print(f"ERROR CRÍTICO: No se pudo generar ni siquiera un PDF básico: {last_error}")
            return None 