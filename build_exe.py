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
    '--onefile',               # Un solo archivo .exe
    '--noconsole',             # Sin ventana de comandos (GUI pura)
    '--windowed',              # Modo ventana
    '--clean',                 # Limpiar temporales
    
    # Incluir todo el código fuente desde el directorio 'src'
    f'--add-data={os.path.join(BASE_DIR, "src")}{os.pathsep}src',
    
    # Recopilar dependencias críticas
    '--collect-all=playwright', # Necesario para el scraper
    '--collect-all=flet',       # Necesario para la UI
    
    # Evitar problemas con bibliotecas dinámicas (opcional pero recomendado en Windows)
    '--hidden-import=flet.canvas',
    '--hidden-import=flet.charts',
]

# Añadir icono si existiera (opcional)
# params.append('--icon=assets/app.ico')

def prepare_build():
    """Limpia directorios de compilación previos."""
    for folder in ['build', 'dist']:
        path = os.path.join(BASE_DIR, folder)
        if os.path.exists(path):
            print(f"[*] Limpiando directorio {folder}...")
            shutil.rmtree(path)

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
