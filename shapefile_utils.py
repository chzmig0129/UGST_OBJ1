import os
import io
import tempfile
# Configurar backend no interactivo antes de importar matplotlib
import matplotlib
matplotlib.use('Agg')  # Usar backend Agg que no depende de Tkinter

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle
from matplotlib_scalebar.scalebar import ScaleBar
import contextily as ctx
from tqdm import tqdm

def plot_shapefile_to_png(shapefile_buffer, output_dir=None):
    """
    Genera imágenes PNG para cada polígono en un archivo shapefile.
    
    Args:
        shapefile_buffer: Buffer de memoria con el archivo shapefile (zip)
        output_dir: Directorio de salida para guardar los PNG (si es None, retorna los PNG como diccionario)
    
    Returns:
        Un diccionario con {id_poligono: png_buffer} si output_dir es None,
        o la ruta del directorio de salida si output_dir se proporciona
    """
    try:
        # Crear un directorio temporal para trabajar con el shapefile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Guardar el buffer del shapefile en un archivo temporal
            temp_zip_path = os.path.join(temp_dir, 'shapefile.zip')
            with open(temp_zip_path, 'wb') as f:
                f.write(shapefile_buffer.getvalue())
            
            # Cargar el archivo shapefile
            gdf = gpd.read_file(f"zip://{temp_zip_path}")
            
            # Asegurarnos de que el GeoDataFrame tenga un CRS válido y esté en Web Mercator
            if gdf.crs is None or gdf.crs != 'EPSG:3857':
                try:
                    gdf = gdf.to_crs('EPSG:3857')
                except Exception as e:
                    print(f"Error al reproyectar: {e}")
                    # Si falla la reproyección, intentamos establecer primero el CRS a WGS84
                    gdf.set_crs('EPSG:4326', inplace=True)
                    gdf = gdf.to_crs('EPSG:3857')

            # Crear el directorio de salida si se proporciona y no existe
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            else:
                # Si no se proporciona directorio, guardaremos en un diccionario de buffers
                png_buffers = {}

            # Calcular el centroide para cada geometría
            gdf['centroid'] = gdf.geometry.centroid

            # Graficar cada polígono individualmente con una barra de progreso
            for idx, row in tqdm(gdf.iterrows(), total=gdf.shape[0], desc="Generando mapas"):
                # Crear figura con dimensiones horizontales
                fig, ax = plt.subplots(figsize=(12, 8))

                # Obtener los límites del polígono
                bounds = row.geometry.bounds
                x_min, y_min, x_max, y_max = bounds

                # Ajustar proporciones para un aspecto horizontal
                width = x_max - x_min
                height = y_max - y_min
                aspect_ratio = 2.2  # Relación de aspecto deseada (ancho / alto)

                # Calcular nuevos límites
                if width / height < aspect_ratio:
                    delta_width = (height * aspect_ratio - width) / 2
                    x_min -= delta_width
                    x_max += delta_width
                else:
                    delta_height = (width / aspect_ratio - height) / 2
                    y_min -= delta_height
                    y_max += delta_height

                # Graficar el polígono
                gdf.iloc[[idx]].plot(ax=ax, edgecolor='#00734C', color='#4CE600', alpha=0.65)

                # Aumentar los márgenes para hacer zoom out y mostrar más entorno
                margin = 50  # Ajusta este valor según el nivel de zoom out deseado

                # Ajustar los límites del gráfico con los nuevos márgenes
                ax.set_xlim(x_min - margin, x_max + margin)
                ax.set_ylim(y_min - margin, y_max + margin)

                # Añadir capa de mapa satelital sin atribución
                try:
                    ctx.add_basemap(
                        ax,
                        source=ctx.providers.Esri.WorldImagery,
                        attribution='',
                        zoom='auto'
                    )
                except Exception as e:
                    print(f"Error al añadir mapa base: {e}")
                
                # Añadir el área en hectáreas en el centro del polígono si existe la columna
                if 'SUP_DIG' in row or 'AREA_HA' in row:
                    area_value = row.get('SUP_DIG', row.get('AREA_HA', 0))
                    plt.text(row['centroid'].x, row['centroid'].y, f"{area_value:.2f} Ha.",
                            fontsize=16, ha='center', color='white')

                # Añadir una barra de escala con fondo transparente
                scalebar = ScaleBar(1, location='lower right', scale_loc='right', units="m",
                                dimension="si-length", font_properties={'size': 8},
                                box_alpha=0, frameon=False)
                ax.add_artist(scalebar)

                # Mantener las proporciones adecuadas
                ax.set_aspect('equal')

                # Configurar los ejes para mostrar ticks en todas las direcciones
                ax.tick_params(top=True, bottom=True, left=True, right=True, labeltop=True, labelright=True)

                # Establecer ticks personalizados
                ax.set_xticks([x_min + 0.20 * width, (x_min + x_max) / 2, x_max - 0.20 * width])
                ax.set_yticks([y_min + 0.20 * height, (y_min + y_max) / 2, y_max - 0.20 * height])

                # Quitar la notación científica y mostrar los números completos
                ax.ticklabel_format(useOffset=False, style='plain')
                ax.yaxis.set_tick_params(rotation=90)

                # Aplicar el formateador para quitar los decimales
                ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{int(x)}'))
                ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{int(y)}'))

                # Añadir un marco exterior alrededor del gráfico
                for spine in ax.spines.values():
                    spine.set_edgecolor('black')
                    spine.set_linewidth(2)

                # Obtener la posición del eje en coordenadas de la figura
                pos = ax.get_position()

                # Definir los desplazamientos para los marcos
                offset1 = 0.04  # Primer marco
                offset2 = 0.058  # Segundo marco

                # Añadir el primer marco
                fig.add_artist(Rectangle(
                    (pos.x0 - offset1, pos.y0 - offset1),
                    pos.width + 2 * offset1,
                    pos.height + 2 * offset1,
                    transform=fig.transFigure,
                    color='black',
                    linewidth=1.5,
                    fill=False
                ))

                # Añadir el segundo marcos
                fig.add_artist(Rectangle(
                    (pos.x0 - offset2, pos.y0 - offset2),
                    pos.width + 2 * offset2,
                    pos.height + 2 * offset2,
                    transform=fig.transFigure,
                    color='black',
                    linewidth=3,
                    fill=False
                ))

                # Mostrar los bordes superiores y derechos del gráfico
                ax.spines['top'].set_visible(True)
                ax.spines['right'].set_visible(True)

                # Obtener el ID del polígono (usar diferentes opciones de nombres de columnas)
                id_poligon = None
                for id_field in ['ID_POLIGON', 'ID_POLIG']:
                    if id_field in row and row[id_field]:
                        id_poligon = row[id_field]
                        break
                
                # Si no se encuentra un ID, usar el índice
                if not id_poligon:
                    id_poligon = f"poligono_{idx}"

                if output_dir:
                    # Guardar el gráfico como PNG en el directorio de salida
                    output_path = os.path.join(output_dir, f"{id_poligon}.png")
                    plt.savefig(output_path, bbox_inches='tight', dpi=300)
                else:
                    # Guardar el gráfico en un buffer de memoria
                    png_buffer = io.BytesIO()
                    plt.savefig(png_buffer, format='png', bbox_inches='tight', dpi=300)
                    png_buffer.seek(0)
                    png_buffers[id_poligon] = png_buffer
                
                plt.close(fig)

            if output_dir:
                return output_dir
            else:
                return png_buffers
    
    except Exception as e:
        print(f"Error al generar imágenes de polígonos: {e}")
        import traceback
        traceback.print_exc()
        return None 