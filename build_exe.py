import PyInstaller.__main__
import os
import sys
import shutil

# Definir rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# El punto de entrada está ahora en src/main.py
MAIN_SCRIPT = os.path.join(BASE_DIR, "src", "main.py")

# Argumentos de PyInstaller optimizados
params = [
    MAIN_SCRIPT,
    '--name=AnimeDL_Pro',
    '--onedir',               # Un solo archivo .exe (Aviso: --onedir suele dar menos falsos positivos)
    '--noconsole',             # Sin ventana de comandos (GUI pura)
    '--windowed',              # Modo ventana
    '--clean',                 # Limpiar temporales
    f'--icon={os.path.join(BASE_DIR, "src", "img", "AnimeDL_Pro.ico")}',  # Icono de la aplicación
    
    # Información de versión (Metadatos) para reducir falsos positivos
    f'--version-file={os.path.join(BASE_DIR, "version_info.txt")}',
    
    # Incluir todo el código fuente y recursos (como la nueva carpeta src/img)
    f'--add-data={os.path.join(BASE_DIR, "src")}{os.pathsep}src',
    
    # Recopilar dependencias críticas
    '--collect-all=playwright', # Necesario para el scraper
    '--collect-all=flet',       # Necesario para la UI
    '--collect-all=flet_desktop', # Necesario para los binarios de la UI en escritorio
    '--collect-all=certifi',    # Asegurar certificados SSL
    
    # Evitar problemas con bibliotecas dinámicas (opcional pero recomendado en Windows)
    '--hidden-import=flet.canvas',
    '--hidden-import=flet.charts',
]

# Añadir icono si existiera (opcional)
# params.append('--icon=assets/app.ico')

def prepare_build():
    """Limpia directorios de compilación previos, archivos caché y temporales."""
    print("[*] Iniciando limpieza de caché y archivos temporales...")
    
    # 1. Limpiar carpetas build y dist
    for folder in ['build', 'dist']:
        path = os.path.join(BASE_DIR, folder)
        if os.path.exists(path):
            print(f"    - Eliminando directorio {folder}...")
            shutil.rmtree(path, ignore_errors=True)
    
    # 2. Limpiar archivos .spec
    for file in os.listdir(BASE_DIR):
        if file.endswith(".spec"):
            print(f"    - Eliminando archivo {file}...")
            os.remove(os.path.join(BASE_DIR, file))
            
    # 3. Limpiar __pycache__ de forma recursiva
    print("    - Eliminando directorios __pycache__...")
    for root, dirs, files in os.walk(BASE_DIR):
        for d in dirs:
            if d == "__pycache__":
                cache_path = os.path.join(root, d)
                shutil.rmtree(cache_path, ignore_errors=True)
    
    print("[*] Limpieza completada.")

if __name__ == "__main__":
    print(f"[*] Directorio base: {BASE_DIR}")
    print(f"[*] Script principal: {MAIN_SCRIPT}")
    
    if not os.path.exists(MAIN_SCRIPT):
        print(f"[!] ERROR: No se encontró el archivo principal en {MAIN_SCRIPT}")
        sys.exit(1)
        
    prepare_build()
    
    print("[*] Iniciando proceso de compilación con PyInstaller...")
    try:
        PyInstaller.__main__.run(params)
        print("\n" + "="*40)
        print("¡COMPILACIÓN FINALIZADA!")
        print(f"EXE generado: {os.path.join(BASE_DIR, 'dist', 'AnimeDL_Pro.exe')}")
        print("="*40)
    except Exception as e:
        print(f"[!] Error crítico en la compilación: {str(e)}")
