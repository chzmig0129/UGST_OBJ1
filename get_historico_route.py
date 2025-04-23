"""
Here is the corrected code for get_historico_poligonos function that should resolve the indentation error.
When adding it to app.py, make sure to:
1. Delete the existing function completely (from @app.route line through the except block)
2. Paste this code in its place
3. Make sure all indentation is using spaces (not tabs)

@app.route('/get-historico-poligonos')
def get_historico_poligonos():
    """Endpoint para cargar y devolver los polígonos históricos como GeoJSON"""
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