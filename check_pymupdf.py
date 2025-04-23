import sys
import os

print("\n=== DIAGNÓSTICO DE PYMUPDF ===")
print(f"Python ejecutable: {sys.executable}")
print(f"Python versión: {sys.version}")
print("\nRutas de búsqueda:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

# Verificar si el módulo fitz existe
try:
    import fitz
    print("\n=== DETALLES DEL MÓDULO FITZ ===")
    print(f"Tipo de fitz: {type(fitz)}")
    print(f"Archivo del módulo: {getattr(fitz, '__file__', 'No disponible')}")
    print(f"Directorio del módulo: {getattr(fitz, '__path__', 'No disponible')}")
    print(f"Versión: {getattr(fitz, 'version', 'No disponible')}")
    
    # Verificar si tiene el método open
    if hasattr(fitz, 'open'):
        print("\n✅ fitz.open ESTÁ DISPONIBLE")
    else:
        print("\n❌ fitz.open NO ESTÁ DISPONIBLE")
        print("Atributos y métodos disponibles:")
        attrs = dir(fitz)
        for attr in [a for a in attrs if not a.startswith('_')]:
            print(f"  - {attr}")
    
except ImportError:
    print("\n❌ No se pudo importar 'fitz'")

# Intentar importar PyMuPDF
try:
    import PyMuPDF
    print("\n=== DETALLES DE PYMUPDF ===")
    print(f"Tipo de PyMuPDF: {type(PyMuPDF)}")
    print(f"Archivo del módulo: {getattr(PyMuPDF, '__file__', 'No disponible')}")
    print(f"Versión: {getattr(PyMuPDF, 'version', 'No disponible')}")
    
    # Verificar si tiene el método open
    if hasattr(PyMuPDF, 'open'):
        print("\n✅ PyMuPDF.open ESTÁ DISPONIBLE")
    else:
        print("\n❌ PyMuPDF.open NO ESTÁ DISPONIBLE")
        
except ImportError:
    print("\n❌ No se pudo importar 'PyMuPDF'")

# Verificar instalación a través de pip
print("\n=== PAQUETES INSTALADOS ===")
try:
    import pkg_resources
    pymupdf_pkg = [p for p in pkg_resources.working_set if p.project_name.lower() in ('pymupdf')]
    if pymupdf_pkg:
        for pkg in pymupdf_pkg:
            print(f"Encontrado: {pkg.project_name} {pkg.version} en {pkg.location}")
    else:
        print("PyMuPDF no aparece en los paquetes instalados")
except Exception as e:
    print(f"Error al verificar paquetes: {e}")

print("\n=== RECOMENDACIONES ===")
print("Si fitz existe pero no tiene 'open':")
print("1. Puede haber otro módulo 'fitz' en conflicto")
print("2. Usar 'import PyMuPDF as fitz' en lugar de 'import fitz'")
print("3. Reinstalar PyMuPDF: pip install --force-reinstall PyMuPDF==1.22.5") 