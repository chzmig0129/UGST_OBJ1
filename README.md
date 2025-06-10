# Sistema de Validación de Polígonos VALGEOUGST

Sistema web desarrollado en Flask para la validación, edición y generación de fichas técnicas de polígonos geoespaciales.

## Características

- **Carga de archivos Excel**: Importación automática de datos de polígonos desde archivos Excel
- **Validación de polígonos**: Visualización y edición interactiva de polígonos en mapas
- **Base de datos integrada**: Almacenamiento persistente de todos los datos
- **Generación de shapefiles**: Exportación de polígonos en formato SHP
- **Fichas técnicas**: Generación automática de fichas técnicas en PDF
- **Validación rápida SHP**: Procesamiento directo de archivos Shapefile

## Configuración del entorno

1. **Crear un entorno virtual**:
   ```bash
   python -m venv venv_new
   ```

2. **Activar el entorno virtual**:
   - Windows:
     ```bash
     venv_new\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv_new/bin/activate
     ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

5. **Acceder a la aplicación**:
   Abra su navegador y vaya a `http://127.0.0.1:5000/`

## Estructura del proyecto

- `app.py` - Aplicación principal de Flask
- `templates/` - Plantillas HTML
- `static/` - Archivos estáticos (CSS, JS, imágenes)
- `uploads/` - Directorio para archivos cargados
- `data/` - Archivos de datos (shapefiles de municipios)
- `utils/` - Utilidades auxiliares
- `requirements.txt` - Lista de dependencias

## Funcionalidades principales

### 1. Validación de Polígonos
- Carga de archivos Excel con datos de polígonos
- Edición interactiva de geometrías en mapas
- Validación automática de áreas y coordenadas
- Detección automática de ubicación (estado/municipio)

### 2. Generación de Excel
- Exportación completa de la base de datos a Excel
- Formato profesional con todas las columnas
- Timestamp automático en el nombre del archivo

### 3. Fichas Técnicas
- Generación de fichas técnicas en PDF
- Mapas automáticos integrados
- Plantillas personalizables

### 4. Procesamiento SHP
- Carga directa de archivos Shapefile
- Validación rápida de geometrías
- Exportación a múltiples formatos

## Dependencias principales

- Flask
- pandas
- geopandas
- shapely
- SQLAlchemy
- openpyxl
- reportlab
- leaflet (frontend)

## Notas importantes

- El sistema utiliza SQLite como base de datos por defecto
- Los archivos temporales se almacenan en el directorio `uploads/`
- Se requiere el shapefile de municipios mexicanos en `data/mun22gw.shp`
- Compatible con archivos Excel (.xlsx, .xls) y Shapefiles (.shp)

## Soporte

Para reportar problemas o solicitar nuevas funcionalidades, contacte al equipo de desarrollo. 