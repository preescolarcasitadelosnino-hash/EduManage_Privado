# ==========================================
# CONFIGURACIÓN GENERAL DEL SISTEMA
# ==========================================

from pathlib import Path

# ==========================================
# RUTAS DEL PROYECTO
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# GOOGLE DRIVE
# ==========================================

# Cuenta de servicio (queda para futuras funciones administrativas)
GOOGLE_CREDENTIALS = BASE_DIR / "credenciales" / "edumanagerinecas-6e3aa69c65be.json"

# OAuth de la aplicación web
GOOGLE_DESKTOP_CLIENT = BASE_DIR / "oauth" / "client_desktop.json"

GOOGLE_TOKEN = BASE_DIR / "oauth" / "token.json"



# ==========================================
# CONFIGURACIÓN DE LA INSTITUCIÓN
# ==========================================

ID_INSTITUCION = "INST-DICA"

CARPETA_ASSETS = "assets"
CARPETA_INSTITUCIONES = "instituciones"

NOMBRE_LOGO = "logo.png"
NOMBRE_ESCUDO = "escudo.png"

RUTA_INSTITUCION = (
    f"{CARPETA_ASSETS}/"
    f"{CARPETA_INSTITUCIONES}/"
    f"{ID_INSTITUCION}"
)
