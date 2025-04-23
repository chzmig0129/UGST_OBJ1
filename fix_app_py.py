"""
This script fixes the indentation issue in the get_historico_poligonos function in app.py.
"""
import re

def fix_app_py():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the pattern to match the function and replace it
    pattern = r"@app\.route\('/get-historico-poligonos'\)\s*def get_historico_poligonos\(\):[^@]*"
    
    # Replacement with proper indentation
    replacement = """@app.route('/get-historico-poligonos')
def get_historico_poligonos():
    \"\"\"Endpoint para cargar y devolver los polígonos históricos como GeoJSON\"\"\"
    try:
        # Ruta al archivo shapefile histórico
        historico_shapefile = "data/HISTORICO_ORDEN_40"
        
        # Leer el shapefile con geopandas
        historico_gdf = gpd.read_file(historico_shapefile)
        
        # Verificar/convertir CRS a WGS84 (EPSG:4326) si es necesario
        if historico_gdf.crs != "EPSG:4326":
            historico_gdf = historico_gdf.to_crs(epsg=4326)
        
        # Convertir a GeoJSON
        geojson_data = json.loads(historico_gdf.to_json())
        
        # Asegurar que tenemos el campo ID_POLIGON (si existe)
        id_field = None
        for field in historico_gdf.columns:
            if field.upper() == 'ID_POLIGON':
                id_field = field
                break
            
        # Agregar información sobre el campo de ID para facilitar el etiquetado en el frontend
        respuesta = {
            'geojson': geojson_data,
            'id_field': id_field
        }
        
        return jsonify(respuesta)
    except Exception as e:
        print(f"Error al cargar el shapefile histórico: {e}")
        return jsonify({'error': str(e)}), 500

"""
    
    # Replace the function in the content
    if re.search(pattern, content):
        updated_content = re.sub(pattern, replacement, content)
        
        # Write the updated content back to the file
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print("Successfully fixed app.py")
    else:
        print("Could not find the function in app.py")

if __name__ == "__main__":
    fix_app_py() 