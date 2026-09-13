import streamlit as st
import re
import os

def flash_set(tipo, mensaje):
    st.session_state["flash_tipo"] = tipo
    st.session_state["flash_mensaje"] = mensaje

def mostrar_flash():
    if "flash_mensaje" in st.session_state:
        tipo = st.session_state.pop("flash_tipo", "info")
        mensaje = st.session_state.pop("flash_mensaje")

        if hasattr(st, tipo):
            getattr(st, tipo)(mensaje)
        else:
            st.info(mensaje)

import re
import os
import sys
import streamlit as st
from datetime import date
from streamlit_searchbox import st_searchbox

# ... (tus demás imports y código) ...



def obtener_ruta_foto(url_foto):
    """
    Convierte enlaces de Google Drive a URLs de descarga/visualización directa
    compatibles con etiquetas de imagen y Streamlit.
    """
    if not url_foto:
        return None
    
    url_str = str(url_foto).strip()
    
    # Si es un enlace de Google Drive, extraer el ID y convertirlo a enlace directo
    if "drive.google.com" in url_str:
        file_id = None
        # Patrón para enlaces tipo /file/d/ID/view
        match_file = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url_str)
        if match_file:
            file_id = match_file.group(1)
        else:
            # Patrón para enlaces tipo ?id=ID
            match_id = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url_str)
            if match_id:
                file_id = match_id.group(1)
        
        if file_id:
            # Este formato le fuerza a Google Drive a entregar la imagen directamente
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        
        return url_str
    
    # Si es otro enlace web http/https común
    if url_str.startswith("http://") or url_str.startswith("https://"):
        return url_str
    
    # Búsqueda local en la carpeta assets
    base_name = os.path.basename(url_str)
    name_no_ext, _ = os.path.splitext(base_name)
    extensiones = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG", ""]
    
    for ext in extensiones:
        nombre_a_probar = name_no_ext + ext if not base_name.endswith(ext) else base_name
        ruta = os.path.join("assets", nombre_a_probar)
        if os.path.exists(ruta):
            return ruta
            
    if os.path.exists(url_str):
        return url_str
        
    return None

def obtener_url_o_ruta_imagen(url_foto):
    if not url_foto:
        return None
    
    str_val = str(url_foto).strip()
    
    # 1. Validar rutas locales, incluyendo las antiguas guardadas sin el
    # prefijo "assets/" (por ejemplo: instituciones/INST-DICA/escudo.png).
    rutas_locales = [str_val]
    ruta_sin_assets = str_val.replace("\\", "/").lstrip("/")
    if ruta_sin_assets.startswith("assets/"):
        rutas_locales.append(ruta_sin_assets)
    else:
        rutas_locales.append(os.path.join("assets", ruta_sin_assets))

    for ruta_local in rutas_locales:
        if os.path.exists(ruta_local):
            return ruta_local
        
    # 2. Validar si es una URL web completa (http/https)
    if str_val.startswith("http://") or str_val.startswith("https://"):
        if "drive.google.com" in str_val:
            # Extraer el ID de un enlace tipo /file/d/ID/view o open?id=ID
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', str_val)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=view&id={file_id}"
            
            match_id = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', str_val)
            if match_id:
                file_id = match_id.group(1)
                return f"https://drive.google.com/uc?export=view&id={file_id}"
        
        return str_val
        
    # 3. Si es directamente un ID de Google Drive (alfanumérico largo sin barras)
    if len(str_val) > 20 and "/" not in str_val and "\\" not in str_val:
        return f"https://drive.google.com/uc?export=view&id={str_val}"
        
    return None
