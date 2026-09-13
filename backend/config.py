# ==========================================
# CONFIGURACIÓN GENERAL DEL SISTEMA
# ==========================================

from pathlib import Path
import os
import streamlit as st


def obtener_configuracion(nombre, predeterminado=None):
    """Lee configuración desde Streamlit Secrets o variables de entorno."""
    try:
        if nombre in st.secrets:
            valor = st.secrets[nombre]
            if valor not in (None, ""):
                return valor
    except Exception:
        pass
    return os.getenv(nombre, predeterminado)

# ==========================================
# BASE DE DATOS (SUPABASE / POSTGRESQL)
# ==========================================

DATABASE_URL = obtener_configuracion("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/edumanager")

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

# Carpeta raíz privada de Drive. Debe configurarse en Secrets/variables de entorno.
# No se usa una carpeta pública predeterminada para evitar mezclar proyectos.
GOOGLE_DRIVE_ROOT = obtener_configuracion("GOOGLE_DRIVE_ROOT", "")

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
