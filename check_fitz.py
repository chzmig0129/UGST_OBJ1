import sys
print(f"Python: {sys.executable}")

# Verificar fitz
try:
    import fitz
    print(f"fitz importado: {fitz}")
    print(f"Tipo de fitz: {type(fitz)}")
    print(f"Versión: {getattr(fitz, 'version', 'No disponible')}")
    print(f"Archivo: {getattr(fitz, '__file__', 'No disponible')}")
    
    # Verificar si fitz tiene el método open
    has_open = hasattr(fitz, 'open')
    print(f"¿fitz tiene el método open?: {has_open}")
    
    # Listar algunos atributos si no tiene open
    if not has_open:
        attrs = [attr for attr in dir(fitz) if not attr.startswith('_')]
        print(f"Atributos disponibles: {', '.join(attrs[:10])}...")
        
except ImportError:
    print("No se pudo importar fitz")

# Verificar ruta de búsqueda
print("\nRutas de búsqueda:")
for path in sys.path:
    print(f"  {path}")

# Verificar PyMuPDF
try:
    import PyMuPDF
    print("\nPyMuPDF importado correctamente")
except ImportError:
    print("\nNo se pudo importar PyMuPDF") 