import sys
import os
import streamlit as st
from streamlit_searchbox import st_searchbox
import datetime
from datetime import date
from backend.usuarios import mostrar_modulo_usuarios
from backend.institucion import mostrar_modulo_institucion
from backend.sedes import mostrar_modulo_sedes
from backend.sectores import mostrar_registro_sector

from backend.db_manager import (
    autenticar_usuario,
    actualizar_ultimo_acceso,
    web_obtener_grados_con_detalle,
    formatear_nombre_grupo
    )
from backend.estudiantes import (
    mostrar_busqueda_estudiantes,
    mostrar_formulario_estudiante,
)
from backend.drive_manager import DriveManager
from backend.utils import obtener_url_o_ruta_imagen

from backend.institucion_db import(
        web_obtener_institucion,
        web_actualizar_institucion
    )

from backend.acudientes import (
    mostrar_formulario_acudiente,
    mostrar_acudientes,
    
    )
from backend.form_navigation import activar_navegacion_enter
from backend.personal import mostrar_consulta_personal, mostrar_formulario_personal
from backend.personal_db import web_obtener_personal_activo
from backend.acudientes_editar import (
        mostrar_edicion_acudiente
    )

from backend.matriculas import (
    mostrar_registro_matricula,
    gestionar_matriculas,
    limpiar_matricula
      
    )
from backend.matriculas_db import (
    web_obtener_matriculas_activas_curso
)

st.set_page_config(
    page_title="EduManager",
    page_icon="assets/edumanager_icon.svg",
)

# ==========================================
# SESIÓN DE USUARIO
# ==========================================

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "rol" not in st.session_state:
    st.session_state.rol = None

if "ultimo_acceso" not in st.session_state:
    st.session_state.ultimo_acceso = None

# ==========================================================
# CONTROL DE PERMISOS
# ==========================================================

def tiene_permiso(*roles):
    """
    Retorna True si el usuario actual pertenece
    a alguno de los roles permitidos.
    """
    return st.session_state.rol in roles

# Importación centralizada: evita cargar ``db_manager`` dos veces con
# nombres de módulo distintos y crear pools independientes en el mismo proceso.
try:
    from backend.db_manager import (
   
    web_obtener_cursos,
    web_obtener_grados,
    web_obtener_grados_completo,
    web_registrar_grado,
    web_actualizar_grado,
    web_eliminar_grado,
    web_obtener_sedes,
    web_obtener_jornadas,
    web_obtener_cursos_completo,
    web_registrar_curso,
    web_eliminar_curso,
    web_actualizar_curso,
    web_generar_codigo_direccion_grupo,
    web_registrar_direccion_grupo,
    web_consultar_direcciones_grupo,
    web_eliminar_direccion_grupo,
    web_registrar_asignatura,
    web_actualizar_asignatura,
    web_obtener_asignaturas,
    web_eliminar_asignatura,
    web_registrar_plan_estudio,
    web_actualizar_horas_plan,
    web_obtener_plan_estudio,
    web_eliminar_plan_estudio,
    web_obtener_asignaturas_sin_asignar,
    web_registrar_asignacion_docente,
    web_obtener_asignaciones_docente,
    web_eliminar_asignacion_docente,
    web_obtener_periodos,
    web_guardar_periodos,
    web_obtener_indicadores,
    web_registrar_indicador,
    web_actualizar_indicador,
    web_eliminar_indicador,
    web_obtener_escala,
    web_guardar_escala,
    web_nivel_para_valor,
    web_obtener_estudiantes_por_curso,
    web_obtener_calificaciones,
    web_guardar_calificaciones_bulk,
    web_guardar_boletin_datos,
    web_obtener_boletin_datos,
    web_datos_para_boletin,
    web_obtener_promedios_periodo,
    web_obtener_boletin_datos_bulk,
    obtener_conexion_directa,
    )
except ImportError as e:
    st.error(f"Error crítico al importar: {e}")
    st.stop()


# 3. Inicialización de estado (esto es vital para que Streamlit no pierda los datos)
if "mat_id_est" not in st.session_state: st.session_state.mat_id_est = ""
if "mat_id_acu" not in st.session_state: st.session_state.mat_id_acu = ""
# Forzamos al sistema a usar UTF-8 en las librerías internas de C (como la de PostgreSQL)
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["LANG"] = "C.UTF-8"

# ==========================================
# LOGIN
# ==========================================

if st.session_state.usuario is None:

    with st.container(border=True):
        col_marca, col_nombre = st.columns([1, 3])
        with col_marca:
            st.image("assets/edumanager_icon.svg", width=112)
        with col_nombre:
            st.markdown("### EduManager")
            st.caption("Gestión educativa institucional")

    # Un formulario nativo garantiza que Enter y el clic envíen los valores
    # actualizados de usuario y contraseña en el mismo momento.
    with st.form("formulario_inicio_sesion"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        boton_ingresar = st.form_submit_button("Ingresar")

    # Evita que Enter en Usuario envíe prematuramente el formulario.
    # Enter en Contraseña sí activa el botón de ingreso.
    activar_navegacion_enter(["Usuario", "Contraseña"], boton_final="Ingresar")

    if boton_ingresar:

        ok, resultado = autenticar_usuario(
        usuario,
        password
)

        if ok:

            # Guardamos el último acceso ANTES de actualizarlo
            st.session_state.usuario = resultado[1]
            st.session_state.rol = resultado[2]
            st.session_state.ultimo_acceso = resultado[4]

            # Actualizamos el último acceso
            actualizar_ultimo_acceso(resultado[0])

            st.success(f"Bienvenido {resultado[1]}")

            st.rerun()

        else:

            st.error(resultado)

    st.stop()

st.markdown("""
<style>
/* ── Sidebar: fondo azul institucional ─────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #1a3a5c !important;
    min-width: 248px !important;
    max-width: 248px !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* ── Todos los textos del sidebar en blanco ─────────────────────────────────── */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: rgba(255,255,255,0.85) !important;
}

/* ============================================================
   MENÚ LATERAL - BOTONES BASE
   ============================================================ */

section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-left: 3px solid transparent !important;

    color: rgba(255,255,255,0.72) !important;

    text-align: left !important;
    justify-content: flex-start !important;

    display: flex !important;
    align-items: center !important;

    width: 100% !important;

    box-shadow: none !important;
}


/* ============================================================
   ENCABEZADOS PRINCIPALES DEL MENÚ
   ============================================================ */

div.element-container:has(.nav-header-marker)
+ div.element-container
.stButton > button {

    font-size: 15px !important;

    font-weight: 700 !important;

    color: rgba(255,255,255,0.95) !important;

    padding: 11px 14px !important;

    background: rgba(255,255,255,0.035) !important;

    border-left: 3px solid transparent !important;

    border-radius: 6px !important;

    letter-spacing: 0.2px !important;
}


div.element-container:has(.nav-header-marker)
+ div.element-container
.stButton > button:hover {

    background: rgba(255,255,255,0.10) !important;

    color: white !important;

    border-left: 3px solid rgba(255,255,255,0.35) !important;
}


//* ============================================================
   SUBMENÚS - IDENTIDAD VERDE
   ============================================================ */

div.element-container:has(.nav-submenu-marker)
+ div.element-container
.stButton > button {

    font-size: 13px !important;

    font-weight: 500 !important;

    color: #8fb393 !important;

    padding: 9px 14px 9px 38px !important;

    /* Fondo verde suave */
    background: rgba(11, 110, 79, 0.45) !important;

    /* Identificador lateral */
    border: none !important;

    border-left: 4px solid #0B6E4F !important;

    border-radius: 5px !important;

}


/* ============================================================
   EFECTO HOVER EN SUBMENÚS
   ============================================================ */

div.element-container:has(.nav-submenu-marker)
+ div.element-container
.stButton > button:hover {

    background: rgba(11, 110, 79, 0.75) !important;

    color: white !important;

    border-left: 4px solid #3BCB8B !important;

    transform: translateX(3px) !important;

}


/* ============================================================
   BOTONES PRINCIPALES SIN SUBMENÚ
   ============================================================ */

div.element-container:has(.nav-main-marker)
+ div.element-container
.stButton > button {

    font-size: 14px !important;

    font-weight: 600 !important;

    color: rgba(255,255,255,0.85) !important;

    padding: 10px 14px !important;

    border-radius: 6px !important;
}


/* ============================================================
   ELEMENTOS INTERNOS DE LOS BOTONES
   ============================================================ */

section[data-testid="stSidebar"] .stButton > button div,
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span {

    text-align: left !important;

    justify-content: flex-start !important;

    margin: 0 !important;

    padding: 0 !important;
}


/* ============================================================
   ELIMINAR EFECTOS DE FOCO
   ============================================================ */

section[data-testid="stSidebar"] .stButton > button:focus {

    box-shadow: none !important;

    outline: none !important;
}


/* ============================================================
   ETIQUETAS Y DIVISIONES
   ============================================================ */

.nav-section-lbl {

    display: block;

    font-size: 14px !important;

    font-weight: 700 !important;

    letter-spacing: 1.6px !important;

    text-transform: uppercase !important;

    color: rgba(255,255,255,0.38) !important;

    padding: 14px 16px 5px 16px !important;

    margin: 0 !important;
}


.nav-divider {

    border: none !important;

    border-top: 1px solid rgba(255,255,255,0.10) !important;

    margin: 6px 12px !important;
}


.nav-footer {

    font-size: 13px !important;

    color: rgba(255,255,255,0.28) !important;

    text-align: center !important;

    padding: 12px 8px 6px !important;
}

/* ── Área de contenido principal y componentes ────────────────────────────── */
section.main > div { padding-top: 1.2rem !important; }

div[data-testid="metric-container"] {
    background: #f0f4f8 !important;
    border: 1px solid #dde3ea !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
}
div[data-testid="metric-container"] label {
    color: #5a6a7a !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #1a3a5c !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}

div[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
}

/* Botones primarios en azul institucional */
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background-color: #1a3a5c !important;
    border-color: #1a3a5c !important;
    color: white !important;
    border-radius: 8px !important;
}
.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #254e7a !important;
    border-color: #254e7a !important;
}

/* ── Estilos generales de formularios y bloques ─────────────────────────────── */
div[data-testid="stVerticalBlock"]{ gap: 0.15rem !important; }
div.element-container{ margin-bottom: 0.35rem !important; }
h1, h2, h3{ margin-bottom: 0.3rem !important; padding-bottom: 0.3rem !important; }
div[data-testid="stMarkdownContainer"] p{ margin-bottom: 0.5rem !important; }
div[data-testid="column"]{ padding-top: 0rem !important; }
hr{ margin-top: 0.25rem !important; margin-bottom: 0.25rem !important; }

/* ── Pestañas (Tabs) ────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{
    gap: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #d9e3ec;
}
.stTabs [data-baseweb="tab"]{
    min-height: 48px;
    background: #eef4fa;
    border-radius: 10px 10px 0 0;
    border: 1px solid #c9d6e5;
    padding: 0 12px;
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #1a3a5c !important;
    transition: all .25s ease;
}
.stTabs [data-baseweb="tab"]:hover{
    background: #dfeaf6;
    color: #0b6e4f !important;
}
.stTabs [aria-selected="true"]{
    background: #1a4f8b !important;
    color: white !important;
    border: 1px solid #1a4f8b !important;
    box-shadow: 0 3px 8px rgba(26,79,139,.25);
}
.stTabs [aria-selected="true"] p{
    color: white !important;
    font-weight: 800 !important;
}
.stTabs [data-baseweb="tab"] p{
    font-size: 16px !important;
    font-weight: 600 !important;
    white-space: nowrap;
}

/* ── Diferenciación visual para submenús ──────────────────────────────────── */
/* Hacemos que los submenús tengan una letra más sutil y compacta */
section[data-testid="stSidebar"] .stButton > button {
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)


@st.dialog("⚠️ Atención: Proceso de Matrícula Pendiente")
def mostrar_modal_salida():
    nombre_estudiante = (
        st.session_state.get("mat_est_nom") or 
        st.session_state.get("estudiante_actual") or 
        "el estudiante"
    )
    
    st.write(f"Estás a punto de abandonar la matrícula de **{nombre_estudiante}**.")
    st.write("Si sales, la información temporal se cancelará y los datos actuales se descartarán.")
    st.write("") 
    
    col_salir, col_continuar = st.columns(2)
    
    with col_continuar:
        if st.button("↩️ Continuar matrícula", use_container_width=True):
            st.session_state.pop("mat_salida_pendiente", None)
            st.session_state.pop("mat_destino_salida", None)
            st.session_state.pop("mat_destino_seccion", None)
            st.rerun()
            
    with col_salir:
        if st.button("❌ Cancelar y salir", type="primary", use_container_width=True):
            # 1. Rescatamos el destino exacto al que dio clic el usuario ANTES de limpiar nada
            destino = st.session_state.get("mat_destino_salida")
            seccion = st.session_state.get("mat_destino_seccion")

            # 2. Limpiamos por completo los datos del proceso de matrícula y banderas
            limpiar_matricula()
            if "_limpiar_matricula_en_proceso" in globals():
                _limpiar_matricula_en_proceso()

            # Borramos todas las variables de control de la matrícula para que el sistema "olvide" que había un proceso activo
            keys_a_borrar = [
                "mat_salida_pendiente", 
                "mat_destino_salida", 
                "mat_destino_seccion", 
                "estudiante_actual", 
                "nuevo_estudiante",
                "mat_est_data",
                "mat_est_nom"
            ]
            for k in keys_a_borrar:
                st.session_state.pop(k, None)
            
            # 3. 🌟 APLICAMOS EL DESTINO Y ACTUALIZAMOS EL WIDGET DEL MENÚ SI EXISTE
            if destino:
                st.session_state["pagina_activa"] = destino
                st.session_state["modulo_activo"] = destino
                # Si tu menú lateral usa un radio button u otra key asociada, la actualizamos también:
                if "menu_sidebar" in st.session_state:
                    st.session_state["menu_sidebar"] = destino
            
            if seccion is not None:
                st.session_state["nav_sec_abierta"] = seccion
                
            # 4. Recargamos la app para aplicar el salto definitivo
            st.rerun()

# ─────────────────────────────────────────────────────────────
# DATOS DE LA INSTITUCIÓN
# ─────────────────────────────────────────────────────────────

from backend.config import ID_INSTITUCION

_inst = web_obtener_institucion(ID_INSTITUCION) or {}

_nombre_inst = _inst.get("nombre_institucion", "Sistema Escolar")
_municipio   = _inst.get("municipio", "")
_depto       = _inst.get("departamento", "")
_telefono    = _inst.get("telefono_principal", "")

# primero intenta usar el escudo
_imagen = _inst.get("escudo_url")

# si no existe usa el logo
if not _imagen:
    _imagen = _inst.get("logo_url")

_imagen_full = obtener_url_o_ruta_imagen(_imagen)


_loc = f"{_municipio}{', ' + _depto if _depto else ''}"

if _imagen_full and _imagen_full.startswith(("http://", "https://")):
    _logo_html = f"""
        <img src="{_imagen_full}"
             style="
                 width:90px;
                 height:90px;
                 object-fit:contain;
                 margin-bottom:10px;
             ">
    """
elif _imagen_full and os.path.exists(_imagen_full):
    import base64

    with open(_imagen_full, "rb") as f:
        imagen64 = base64.b64encode(f.read()).decode()

    _logo_html = f"""
        <img src="data:image/png;base64,{imagen64}"
             style="
                 width:90px;
                 height:90px;
                 object-fit:contain;
                 margin-bottom:10px;
             ">
    """
else:
    _logo_html = """
        <div style='font-size:60px;margin-bottom:8px'>
            🏫
        </div>
    """
st.sidebar.markdown(
    f"<div style='background:#15304e;padding:30px 15px 18px;text-align:center'>"
    f"{_logo_html}"
    f"<div style='font-weight:700;font-size:16.5px;line-height:1.35;color:white'>{_nombre_inst}</div>"
    f"{'<div style=\"font-size:11px;opacity:.55;margin-top:4px\">' + _loc + '</div>' if _loc else ''}"
    f"{'<div style=\"font-size:10.5px;opacity:.45;margin-top:2px\">📞 ' + _telefono + '</div>' if _telefono else ''}"
    f"</div>",
    unsafe_allow_html=True
)

if st.session_state.get("mat_salida_pendiente"):
    mostrar_modal_salida()

# ── Menú de navegación ────────────────────────────────────────────────────────
_OPCIONES_NAV = [
    "Inicio",
    "🆕 Registrar Estudiante",
    "🆕 Registrar Acudiente",
    "🆕 Registrar Personal",
    "🆕 Registrar Matrícula",
    "📋 Gestionar Matrículas",
    "📚 Gestionar Grupos",
    "🧑‍🏫 Direcciones de Grupo",
    "📖 Asignaturas",
    "📋 Plan de Estudio",
    "👩‍🏫 Asignación Docente",
    "📅 Períodos",
    "📝 Indicadores",
    "📊 Notas",
    "📄 Boletines",
    "🔎 Consultar Estudiantes",
    "🔎 Consultar Acudientes",
    "🔎 Consultar Personal",
    "👤 Usuarios",
    "🏫 Institución",
    "⚙️ Configuración",
    "📚 Sectores",
    "📚 Grados",
    "🏫 Sedes",
    "⚖️ Escala de Valoración",
]

# Inicializar página activa (con guarda defensiva)
if "pagina_activa" not in st.session_state or st.session_state["pagina_activa"] not in _OPCIONES_NAV:
    st.session_state["pagina_activa"] = "Inicio"

# Resolver navegación interna (interceptando si hay matrícula en curso)
# Resolver navegación interna (interceptando si hay matrícula en curso)
if "mat_nav_destino" in st.session_state:
    _destino = st.session_state.pop("mat_nav_destino")
    if _destino in _OPCIONES_NAV:
        
        # Verificamos si hay un proceso de matrícula activo con datos temporales
        proceso_activo = st.session_state.get("estudiante_actual") or st.session_state.get("nuevo_estudiante")
        
        # Si estás en el módulo de matrícula y hay datos a medias:
        if proceso_activo and st.session_state.get("pagina_activa") == "📝 Registro de Matrícula":
            # 1. Activamos la ventana emergente
            st.session_state["mat_salida_pendiente"] = True
            # 2. Guardamos el destino al que querías ir para usarlo si decides cancelar
            st.session_state["mat_destino_salida"] = _destino
        else:
            # 🌟 ESTO FALTABA: Si no hay matrícula activa, navega de forma normal de inmediato
            st.session_state["pagina_activa"] = _destino
            st.rerun()

# CSS dinámico: resalta el botón activo
def _css_key(opcion_str: str) -> str:
    """Convierte el nombre de opción en un id CSS seguro."""
    return (opcion_str
            .replace(" ", "_")
            .replace("🆕", "nuevo")
            .replace("🔎", "buscar")
            .replace("⚙️", "cfg")
            .replace("–", "")
            .strip("_"))

_active_css = _css_key(st.session_state["pagina_activa"])
st.markdown(f"""
<style>
div:has(#nav-{_active_css}) + div .stButton > button {{
    background: rgba(255,255,255,0.15) !important;
    color: white !important;
    border-left: 3px solid #60a5fa !important;
    font-weight: 600 !important;
}}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONTROL DE SALIDA DEL MÓDULO MATRÍCULA
# =========================================================

def _hay_matricula_en_proceso():

    return bool(
        st.session_state.get("mat_est_data")
        or st.session_state.get("id_est_mat")
    )


def _nombre_estudiante_matricula():

    nombre = st.session_state.get("mat_est_nom")

    if nombre:
        return str(nombre).strip()

    return "el estudiante seleccionado"


def _limpiar_matricula_en_proceso():

    # Eliminar estados temporales propios de Matrícula
    claves_matricula = [
        clave
        for clave in list(st.session_state.keys())
        if clave.startswith("mat_")
    ]

    for clave in claves_matricula:
        st.session_state.pop(clave, None)

    # Estados del estudiante que pudieron quedar
    # activos durante el proceso de matrícula
    claves_adicionales = [
        "id_est_mat",
        "estudiante_actual",
        "modo_edicion_estudiante",
    ]

    for clave in claves_adicionales:
        st.session_state.pop(clave, None)

def _nav_btn(
    icon,
    label,
    pagina,
    sec_key=None,
    indent=False
    ):
    """
    Botón de navegación.

    - Los botones principales tienen estilo propio.
    - Los submenús tienen sangría y estilo diferente.
    - Conserva toda la lógica actual de navegación.
    - Solicita confirmación al abandonar una matrícula.
    """

    activa = (
        st.session_state.get(
            "pagina_activa"
        ) == pagina
    )


    # =====================================================
    # MARCADOR VISUAL DEL TIPO DE BOTÓN
    # =====================================================

    if indent:

        st.sidebar.markdown(
            '<div class="nav-submenu-marker"></div>',
            unsafe_allow_html=True
        )

    else:

        st.sidebar.markdown(
            '<div class="nav-main-marker"></div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # BOTÓN
    # =====================================================

    boton_presionado = st.sidebar.button(
        f"{icon}  {label}",
        key=f"nav_{pagina}",
        use_container_width=True,
        type="primary" if activa else "secondary",
    )


    # =====================================================
    # SI NO SE PRESIONÓ EL BOTÓN
    # =====================================================

    if not boton_presionado:

        return


    # =====================================================
    # OBTENER LA PÁGINA ACTUAL
    # =====================================================

    pagina_anterior = st.session_state.get(
        "pagina_activa"
    )


    # =====================================================
    # SI YA ESTAMOS EN LA MISMA PÁGINA
    # =====================================================

    if pagina == pagina_anterior:

        return


    # =====================================================
    # CONFIRMAR SALIDA DE MATRÍCULA
    # =====================================================

    if (

        pagina_anterior
        == "🆕 Registrar Matrícula"

        and _hay_matricula_en_proceso()

    ):

        st.session_state[
            "mat_salida_pendiente"
        ] = True

        st.session_state[
            "mat_destino_salida"
        ] = pagina

        st.session_state[
            "mat_destino_seccion"
        ] = sec_key

        st.rerun()


    # =====================================================
    # LIMPIAR ESTADO DEL MÓDULO ESTUDIANTES
    # =====================================================

    if pagina_anterior == "🔎 Consultar Estudiantes":

        claves_estudiantes = [

            "estudiante_actual",

            "nuevo_estudiante",

            "modo_edicion_estudiante",

            "buscar_estudiante",

            "estudiantes_encontrados",

            "data_estudiantes",

            "mensaje_exito_estudiante",

            "estudiante_actualizado",

        ]


        for clave in claves_estudiantes:

            st.session_state.pop(
                clave,
                None
            )


        st.session_state.pop(
            "modulo_activo",
            None
        )


    # =====================================================
    # CAMBIAR DE PÁGINA
    # =====================================================

    st.session_state[
        "pagina_activa"
    ] = pagina


    # =====================================================
    # ACTUALIZAR MÓDULO ACTIVO
    # =====================================================

    if pagina == "🔎 Consultar Estudiantes":

        st.session_state[
            "modulo_activo"
        ] = "estudiantes"

    else:

        st.session_state[
            "modulo_activo"
        ] = pagina


    # =====================================================
    # MANTENER ABIERTA LA SECCIÓN
    # =====================================================

    if sec_key is not None:

        st.session_state[
            "nav_sec_abierta"
        ] = sec_key


    st.rerun()





# ── Mapa página → sección ─────────────────────────────────────────────────────
_PAGINA_A_SEC = {
    "🆕 Registrar Matrícula":   "matricula",
    "📋 Gestionar Matrículas":  "matricula",
    "🆕 Registrar Estudiante":  "personas",
    "🆕 Registrar Acudiente":   "personas",
    "🆕 Registrar Personal":    "personas",
    "📚 Gestionar Grupos":      "academico",
    "🧑‍🏫 Direcciones de Grupo": "academico",
    "📖 Asignaturas":           "academico",
    "📋 Plan de Estudio":       "academico",
    "👩‍🏫 Asignación Docente":   "academico",
    "📅 Períodos":              "academico",
    "📝 Indicadores":           "academico",
    "📊 Notas":                 "academico",
    "📄 Boletines":             "academico",
    "⚖️ Escala de Valoración":  "sistema",
    "🔎 Consultar Estudiantes": "consultas",
    "🔎 Consultar Acudientes":  "consultas",
    "🔎 Consultar Personal":    "consultas",
    "👤 Usuarios":              "sistema",
    "🏫 Institución":           "sistema",
    "📚 Sectores":              "sistema",
    "⚙️ Configuración":         "sistema",
    "📚 Grados":                 "sistema",
    "🏫 Sedes":                  "sistema",
}

_pagina = st.session_state["pagina_activa"]

# Inicializar sección abierta: la que contiene la página actual
if "nav_sec_abierta" not in st.session_state:
    st.session_state["nav_sec_abierta"] = _PAGINA_A_SEC.get(_pagina)

_sec = st.session_state["nav_sec_abierta"]   # shorthand

def _sec_hdr(icon: str, label: str, sec_key: str) -> bool:
    """
    Cabecera principal colapsable del menú.

    Devuelve True si la sección está abierta.
    """

    abierta = (
        st.session_state.get(
            "nav_sec_abierta"
        ) == sec_key
    )

    flecha = "▾" if abierta else "▸"

    # Marcador visual para diferenciar
    # los encabezados de los submenús.
    st.sidebar.markdown(
        '<div class="nav-header-marker"></div>',
        unsafe_allow_html=True
    )

    if st.sidebar.button(
        f"{flecha}  {icon}  {label}",
        key=f"sec_{sec_key}",
        use_container_width=True,
    ):

        if abierta:

            st.session_state[
                "nav_sec_abierta"
            ] = None

        else:

            st.session_state[
                "nav_sec_abierta"
            ] = sec_key

        st.rerun()

    return abierta

# ─────────────────────────────────────────────────────────────
# Información del usuario
# ─────────────────────────────────────────────────────────────

st.sidebar.markdown("---")

st.sidebar.markdown(f"### 👤 {st.session_state.usuario}")

st.sidebar.write(f"**Rol:** {st.session_state.rol}")

if st.session_state.ultimo_acceso:

    st.sidebar.write(
        f"**Último acceso:** {st.session_state.ultimo_acceso.strftime('%d/%m/%Y %H:%M')}"
    )

else:

    st.sidebar.write("**Primer acceso al sistema**")

st.sidebar.markdown("---")

# ─── Inicio ──────────────────────────────────────────────────────────────────
_nav_btn("🏠", "Inicio", "Inicio")

# ─── Matrícula ────────────────────────────────────────────────────────────────
if _sec_hdr("📝", "Matrícula", "matricula"):
    _nav_btn("📋", "Nueva Matrícula",      "🆕 Registrar Matrícula",  "matricula", indent=True)
    _nav_btn("🗂️", "Gestionar Matrículas", "📋 Gestionar Matrículas", "matricula", indent=True)

# ─── Comunidad Educativa ──────────────────────────────────────────────────────
if _sec_hdr("👥", "Comunidad Educativa", "personas"):
    _nav_btn("👨‍🎓", "Estudiantes", "🆕 Registrar Estudiante", "personas", indent=True)
    _nav_btn("👨‍👩‍👧", "Acudientes",  "🆕 Registrar Acudiente",  "personas", indent=True)
    _nav_btn("👨‍🏫", "Personal",    "🆕 Registrar Personal",   "personas", indent=True)

# ─── Estructura Académica ─────────────────────────────────────────────────────
if _sec_hdr("📚", "Estructura Académica", "est_academica"):
    _nav_btn("📅", "Períodos",             "📅 Períodos",             "est_academica", indent=True)
    _nav_btn("🏫", "Grados",               "📚 Grados",               "est_academica", indent=True)
    _nav_btn("🗂️", "Grupos",               "📚 Gestionar Grupos",     "est_academica", indent=True)
    _nav_btn("📖", "Asignaturas",          "📖 Asignaturas",          "est_academica", indent=True)
    _nav_btn("📋", "Plan de Estudio",      "📋 Plan de Estudio",      "est_academica", indent=True)
    _nav_btn("📝", "Indicadores / Logros", "📝 Indicadores",          "est_academica", indent=True)

# ─── Operación Académica ──────────────────────────────────────────────────────
if _sec_hdr("📊", "Operación Académica", "op_academica"):
    _nav_btn("🧑‍🏫", "Directores de Grupo", "🧑‍🏫 Direcciones de Grupo", "op_academica", indent=True)
    _nav_btn("👩‍🏫", "Asignación Docente",  "👩‍🏫 Asignación Docente",  "op_academica", indent=True)
    _nav_btn("📊", "Calificaciones / Notas", "📊 Notas",             "op_academica", indent=True)
    _nav_btn("📄", "Boletines",            "📄 Boletines",            "op_academica", indent=True)

# ─── Consultas ────────────────────────────────────────────────────────────────
if _sec_hdr("🔍", "Consultas y Listados", "consultas"):
    _nav_btn("👨‍🎓", "Estudiantes", "🔎 Consultar Estudiantes", "consultas", indent=True)
    _nav_btn("👨‍🎓", "Acudientes",  "🔎 Consultar Acudientes",  "consultas", indent=True)
    _nav_btn("👨‍🏫", "Personal",    "🔎 Consultar Personal",    "consultas", indent=True)

# ─── Sistema ──────────────────────────────────────────────────────────────────
if _sec_hdr("⚙️", "Sistema", "sistema"):
    if tiene_permiso("ADMIN"):
        _nav_btn("👤", "Usuarios",             "👤 Usuarios",             "sistema", indent=True)
        _nav_btn("🏫", "Institución",          "🏫 Institución",          "sistema", indent=True)
        _nav_btn("📚", "Sectores",             "📚 Sectores",             "sistema", indent=True)
        _nav_btn("🏫", "Sedes",                "🏫 Sedes",                "sistema", indent=True)
        _nav_btn("⚖️", "Escala de Valoración", "⚖️ Escala de Valoración", "sistema", indent=True)
        _nav_btn("⚙️", "Configuración Gral.",  "⚙️ Configuración",        "sistema", indent=True)

# Footer
st.sidebar.markdown(
    '<div class="nav-footer">DICA Director Escolar v1.0</div>',
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):

    st.session_state.usuario = None
    st.session_state.rol = None

    st.rerun()

# ── Flash message: persiste mensajes de feedback a través de st.rerun() ─────
def _flash_set(level: str, msg: str):
    """Guarda un mensaje para mostrarlo después del siguiente rerun."""
    st.session_state["_flash_msg"] = (level, str(msg))

def _flash_show():
    """Muestra y limpia el mensaje flash pendiente (si existe)."""
    if "_flash_msg" in st.session_state:
        level, msg = st.session_state.pop("_flash_msg")
        getattr(st, level)(msg)


# Variable de compatibilidad: el resto del archivo usa `opcion`
opcion = st.session_state["pagina_activa"]


# --- 🏠 PANTALLA: INICIO ---



# ── Mostrar mensaje flash de operaciones anteriores ─────────────────────
_flash_show()
if opcion == "👤 Usuarios":

    mostrar_modulo_usuarios()


elif opcion == "🏫 Institución":

    mostrar_modulo_institucion()

elif opcion == "🔎 Consultar Estudiantes":
    mostrar_busqueda_estudiantes()

elif opcion == "🔎 Consultar Acudientes":
    mostrar_acudientes()

elif opcion == "Inicio":
    import base64 as _b64
    from datetime import date as _date

    # ── Datos institucionales ──────────────────────────────────────────────────
    _i = web_obtener_institucion(ID_INSTITUCION) or {}
    _nom        = _i.get("nombre_institucion", "Institución Educativa")
    _rector     = _i.get("nombre_rector", "")
    _municipio  = _i.get("municipio", "")
    _depto      = _i.get("departamento", "")
    _nit        = _i.get("nit_dane", "")
    # Primero intenta usar el escudo
    _logo_p = _i.get("escudo_url", "")

    # Si no existe, usa el logo
    if not _logo_p:
        _logo_p = _i.get("logo_url", "")

# Estas líneas VAN FUERA del if
    _logo_full2 = os.path.join("assets", _logo_p) if _logo_p else ""
    _ano = _date.today().year

    # Logo → base64
    _logo_b64 = ""

    if _logo_full2 and os.path.exists(_logo_full2):
        with open(_logo_full2, "rb") as _lf:
            _logo_b64 = _b64.b64encode(_lf.read()).decode()

    _ubicacion = ", ".join(p for p in [_municipio, _depto] if p)

    nit_html = f"NIT / DANE: {_nit}&nbsp;&middot;&nbsp;" if _nit else ""

    st.markdown(f"""
    <div style="text-align:center; padding:30px">

    <h1>{_nom}</h1>

    <img
    src="data:image/png;base64,{_logo_b64}"
    width="180">

    <p>{_municipio}</p>

    <p>{_rector}</p>

    </div>
    """, unsafe_allow_html=True)


elif opcion == "🔎 Consultar Personal":
    mostrar_consulta_personal()
#==========================================
# 🎨 FORMULARIOS
# ==========================================

# --- 🆕 PANTALLA: REGISTRAR ESTUDIANTE ---
elif opcion == "🆕 Registrar Estudiante":
    mostrar_formulario_estudiante(modo="nuevo")


# --- 🆕 PANTALLA: REGISTRAR ACUDIENTE ---
elif opcion == "🆕 Registrar Acudiente":
    mostrar_formulario_acudiente()

# --- 🆕 PANTALLA: REGISTRAR PERSONAL ---
elif opcion == "🆕 Registrar Personal":
    mostrar_formulario_personal()
elif opcion == "🆕 Registrar Matrícula":

     mostrar_registro_matricula()
    
elif opcion == "📋 Gestionar Matrículas":

    gestionar_matriculas()

# ==========================================
# 📋 GESTIONAR MATRÍCULAS
# ==========================================
elif opcion == "📋 Gestionar Matrículas":

    gestionar_matriculas()


elif opcion == "📚 Sectores":
    
    mostrar_registro_sector()  


# ==========================================
# ⚙️ CONFIGURACIÓN INSTITUCIONAL
# ==========================================
elif opcion == "⚙️ Configuración":
    st.title("⚙️ Configuración de la Institución")
    st.write("Complete aquí los datos de su institución. Se mostrarán en el encabezado y en los documentos generados.")

    inst = st.session_state.get("inst_data") or {}

    st.markdown("### 🏫 Identidad de la Institución")
    col1, col2 = st.columns(2)
    with col1:
        cfg_nombre = st.text_input("Nombre de la institución*", value=inst.get("nombre_institucion", ""))
        cfg_nit    = st.text_input("NIT / Código DANE", value=inst.get("nit_dane", "") or "")
        cfg_res    = st.text_input("Resolución de aprobación", value=inst.get("resolucion_aprobacion", "") or "")
    with col2:
        cfg_dir    = st.text_input("Dirección principal*", value=inst.get("direccion_principal", "") or "")
        cfg_tel    = st.text_input("Teléfono de contacto", value=inst.get("telefono_principal", "") or "")
        cfg_email  = st.text_input("Correo institucional", value=inst.get("email_institucional", "") or "")

    col3, col4 = st.columns(2)
    with col3:
        cfg_mpio   = st.text_input("Municipio*", value=inst.get("municipio", "") or "")
    with col4:
        cfg_depto  = st.text_input("Departamento*", value=inst.get("departamento", "") or "")

    st.write("---")
    st.markdown("### 👤 Rector / Director")
    col5, col6 = st.columns(2)
    with col5:
        cfg_rector = st.text_input("Nombre del rector o director", value=inst.get("nombre_rector", "") or "")
    with col6:
        cfg_correo_rector = st.text_input("Correo del rector", value=inst.get("correo_rector", "") or "")

    st.write("---")
    st.markdown("### 🖼️ Imágenes de la institución")
    st.info("Suba las imágenes en formato JPG o PNG. Se mostrarán en el menú, documentos y boletines.")

    col_img1, col_img2 = st.columns(2)

    # ── Logo principal ────────────────────────────────────────────────────────
    with col_img1:
        st.markdown("**Logo principal**")
        st.caption("Aparece en el menú lateral y en el encabezado de los boletines.")
        logo_actual = inst.get("logo_url", "") or ""
        logo_actual_src = obtener_url_o_ruta_imagen(logo_actual)
        if logo_actual_src:
            st.image(logo_actual_src, width=140, caption="Logo actual")
        else:
            st.caption("Sin logo cargado actualmente.")
        archivo_logo = st.file_uploader("Subir nuevo logo", type=["jpg", "jpeg", "png"],
                                        key="upload_logo")
        cfg_logo_url = logo_actual
        if archivo_logo is not None:
            ext = archivo_logo.name.split(".")[-1].lower()
            cfg_logo_url = f"logo_INST-DICA.{ext}"

    # ── Escudo / imagen secundaria ─────────────────────────────────────────────
    with col_img2:
        st.markdown("**Escudo / imagen secundaria**")
        st.caption("Puede ser el escudo, bandera u otra imagen institucional.")
        escudo_actual = inst.get("escudo_url", "") or ""
        escudo_actual_src = obtener_url_o_ruta_imagen(escudo_actual)
        if escudo_actual_src:
            st.image(escudo_actual_src, width=140, caption="Escudo actual")
        else:
            st.caption("Sin escudo cargado actualmente.")
        archivo_escudo = st.file_uploader("Subir escudo / imagen secundaria",
                                          type=["jpg", "jpeg", "png"], key="upload_escudo")
        cfg_escudo_url = escudo_actual
        if archivo_escudo is not None:
            ext2 = archivo_escudo.name.split(".")[-1].lower()
            cfg_escudo_url = f"escudo_INST-DICA.{ext2}"

    st.write("---")
    st.markdown("### 💬 Eslogan institucional")
    cfg_eslogan = st.text_input(
        "Eslogan / lema",
        value=inst.get("eslogan", "") or "",
        placeholder="Ej: DESARROLLANDO INTELIGENCIA PARA LA EXCELENCIA",
        help="Aparece en el encabezado de los boletines, debajo del nombre de la institución."
    )

    st.write("---")
    st.markdown("### 📝 Misión y Visión")
    cfg_mision = st.text_area("Misión institucional", value=inst.get("mision", "") or "", height=100)
    cfg_vision = st.text_area("Visión institucional", value=inst.get("vision", "") or "", height=100)

    st.write("---")
    if st.button("💾 Guardar configuración", use_container_width=True, type="primary"):
        if not cfg_nombre.strip() or not cfg_dir.strip() or not cfg_mpio.strip() or not cfg_depto.strip():
            st.error("❌ Los campos marcados con * son obligatorios.")
        else:
            with st.spinner("Guardando..."):
                try:
                    if archivo_logo is not None or archivo_escudo is not None:
                        drive = DriveManager()
                        carpeta_institucion = drive.obtener_carpeta_institucion(
                            cfg_nombre.strip()
                        )
                        if archivo_logo is not None:
                            ext_logo = archivo_logo.name.split(".")[-1].lower()
                            cfg_logo_url = drive.subir_archivo_streamlit(
                                archivo_logo,
                                f"LOGO_INSTITUCION.{ext_logo}",
                                carpeta_institucion,
                                hacer_publico=True,
                            )
                        if archivo_escudo is not None:
                            ext_escudo = archivo_escudo.name.split(".")[-1].lower()
                            cfg_escudo_url = drive.subir_archivo_streamlit(
                                archivo_escudo,
                                f"ESCUDO_INSTITUCION.{ext_escudo}",
                                carpeta_institucion,
                                hacer_publico=True,
                            )
                except Exception as error_drive:
                    st.error(f"❌ No se pudieron guardar las imágenes en Google Drive: {error_drive}")
                    st.stop()

                ok, msg = web_actualizar_institucion(
                    "INST-DICA",
                    cfg_nombre.strip(), cfg_nit.strip(), cfg_res.strip(),
                    cfg_dir.strip(), cfg_tel.strip(),
                    cfg_mpio.strip(), cfg_depto.strip(),
                    cfg_email.strip(), cfg_rector.strip(), cfg_correo_rector.strip(),
                    cfg_mision.strip(), cfg_vision.strip(), cfg_logo_url,
                    cfg_eslogan.strip(), cfg_escudo_url
                )

            if ok:
                if "inst_data" in st.session_state:
                    del st.session_state["inst_data"]
                _flash_set("success", f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

# ==========================================
# 📚 GESTIONAR GRUPOS
# ==========================================
elif opcion == "📚 Gestionar Grupos":
    st.title("📚 Gestionar Grupos")
    st.write("Cree y administre los grupos institucionales permanentes.")

    # ── Cargar catálogos enriquecidos ────────────────────────────────────────
    grados_detalle = web_obtener_grados_con_detalle()  # [{id_grado, nombre_grado, nivel, orden}, ...]
    sedes          = web_obtener_sedes()               # [(id_sede, nombre_sede), ...]
    jornadas       = web_obtener_jornadas()            # [(id_jornada, nombre_jornada), ...]

    if not grados_detalle or not sedes or not jornadas:
        st.error("❌ No se pudieron cargar los catálogos necesarios. Verifique la conexión.")
        st.stop()

    # ── Formulario de creación con filtro en cascada dinámico ────────────────
    st.markdown("### ➕ Crear nuevo grupo")

    # Extraer niveles únicos
    niveles_disponibles = sorted(list(set(g["nivel"] for g in grados_detalle)))

    # 1. Selector de Nivel FUERA del form para que actúe de forma dinámica al instante
    sel_nivel = st.selectbox("Seleccione el Nivel educativo primero*", niveles_disponibles, key="crear_grupo_nivel")

    with st.form("form_crear_grupo", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Filtrar los grados que pertenecen únicamente al nivel seleccionado arriba
            grados_filtrados = [g for g in grados_detalle if g["nivel"] == sel_nivel]
            mapa_grados = {g['nombre_grado']: g['id_grado'] for g in grados_filtrados}
            
            sel_grado_label = st.selectbox("Grado*", list(mapa_grados.keys()) if mapa_grados else ["Sin grados"])
            
        with col2:
            sel_grupo = st.text_input("Número / Letra de grupo*", value="01",
                                     help="Ej: 01, 02, A, B")

        col3, col4 = st.columns(2)
        with col3:
            mapa_sedes = {ns: is_ for is_, ns in sedes}
            sel_sede   = st.selectbox("Sede*", list(mapa_sedes.keys()))
        with col4:
            mapa_jornadas = {nj: ij for ij, nj in jornadas}
            sel_jornada   = st.selectbox("Jornada*", list(mapa_jornadas.keys()))

        btn_crear = st.form_submit_button("💾 Crear grupo", use_container_width=True)

    if btn_crear:
        if not mapa_grados or sel_grado_label == "Sin grados":
            st.error("❌ Seleccione un grado válido.")
        else:
            id_grado_sel  = mapa_grados[sel_grado_label]
            id_sede_sel   = mapa_sedes[sel_sede]
            id_jornada_sel = mapa_jornadas[sel_jornada]
            grupo_limpio  = sel_grupo.strip().upper()

            if not grupo_limpio:
                st.error("❌ El número o letra de grupo es obligatorio.")
            else:
                num_grado = id_grado_sel.split("-")[-1].lstrip("0") or "0"
                jor_sufijo = id_jornada_sel.split("-")[-1][0].upper()
                id_curso_nuevo = f"CUR-{num_grado}{grupo_limpio}-{jor_sufijo}"

                with st.spinner("Creando grupo..."):
                    ok, msg = web_registrar_curso(
                        id_curso_nuevo, id_grado_sel, grupo_limpio,
                        id_sede_sel, id_jornada_sel
                    )
                if ok:
                    st.success(f"✅ {msg}  ·  Código asignado: **{id_curso_nuevo}**")
                    if "cursos_completo_cache" in st.session_state:
                        del st.session_state["cursos_completo_cache"]
                else:
                    st.error(f"❌ {msg}")

    # ── Tabla de grupos existentes ─────────────────────────────────────────────
    st.write("---")
    st.markdown("### 📋 Grupos registrados")

    if "cursos_completo_cache" not in st.session_state:
        st.session_state.cursos_completo_cache = web_obtener_cursos_completo()

    cursos_list = st.session_state.cursos_completo_cache

    if st.button("🔄 Actualizar lista", key="grp_refresh"):
        if "cursos_completo_cache" in st.session_state:
            del st.session_state["cursos_completo_cache"]
        st.rerun()

    ids_filtrados = {c["id_curso"] for c in cursos_list}
    if st.session_state.get("grp_edit_id") not in ids_filtrados:
        st.session_state.pop("grp_edit_id", None)
    if st.session_state.get("grp_confirm_del") not in ids_filtrados:
        st.session_state.pop("grp_confirm_del", None)

    if cursos_list:
        st.caption(f"Total: {len(cursos_list)} grupo(s)")

        hdr = st.columns([2, 3, 1, 3, 3, 1, 1])
        for col, label in zip(hdr, ["Código", "Grado", "Grupo", "Sede", "Jornada", "", ""]):
            col.markdown(f"**{label}**")
        st.divider()

        for cur in cursos_list:
            cid = cur["id_curso"]

            if st.session_state.get("grp_edit_id") == cid:
                with st.container(border=True):
                    st.markdown(f"**✏️ Editando grupo: {cid}**")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        mapa_g = {g["nombre_grado"]: g["id_grado"] for g in grados_detalle}
                        grado_actual_label = cur["grado"]
                        
                        edit_grado = st.selectbox(
                            "Grado*", list(mapa_g.keys()),
                            index=list(mapa_g.keys()).index(grado_actual_label)
                                if grado_actual_label in mapa_g else 0,
                            key=f"eg_{cid}_grado"
                        )
                    with ec2:
                        edit_grupo = st.text_input("Grupo*", value=cur["grupo"],
                                                   key=f"eg_{cid}_grupo")

                    ec4, ec5 = st.columns(2)
                    with ec4:
                        mapa_s = {ns: is_ for is_, ns in sedes}
                        sede_idx = list(mapa_s.keys()).index(cur["sede"]) \
                                   if cur["sede"] in mapa_s else 0
                        edit_sede = st.selectbox("Sede*", list(mapa_s.keys()),
                                                 index=sede_idx,
                                                 key=f"eg_{cid}_sede")
                    with ec5:
                        mapa_j = {nj: ij for ij, nj in jornadas}
                        jornada_idx = list(mapa_j.keys()).index(cur["jornada"]) \
                                      if cur["jornada"] in mapa_j else 0
                        edit_jornada = st.selectbox("Jornada*", list(mapa_j.keys()),
                                                    index=jornada_idx,
                                                    key=f"eg_{cid}_jornada")

                    ba1, ba2 = st.columns(2)
                    if ba1.button("💾 Guardar cambios", key=f"eg_{cid}_save",
                                  use_container_width=True):
                        ok, msg = web_actualizar_curso(
                            cid,
                            mapa_g[edit_grado],
                            edit_grupo.strip().upper(),
                            mapa_s[edit_sede],
                            mapa_j[edit_jornada]
                        )
                        if ok:
                            _flash_set("success", f"✅ {msg}")
                        else:
                            _flash_set("error", f"❌ {msg}")
                        st.session_state.pop("grp_edit_id", None)
                        st.session_state.pop("cursos_completo_cache", None)
                        st.rerun()
                    if ba2.button("✖ Cancelar", key=f"eg_{cid}_cancel",
                                  use_container_width=True):
                        st.session_state.pop("grp_edit_id", None)
                        st.rerun()

            else:
                row = st.columns([2, 3, 1, 3, 3, 1, 1])
                row[0].write(cid)
                row[1].write(cur["grado"])
                row[2].write(cur["grupo"])
                row[3].write(cur["sede"])
                row[4].write(cur["jornada"])
                if row[5].button("✏️", key=f"grp_edit_{cid}",
                                 help="Editar grupo"):
                    st.session_state["grp_edit_id"] = cid
                    st.rerun()
                if row[6].button("🗑️", key=f"grp_del_{cid}",
                                 help="Eliminar grupo"):
                    st.session_state["grp_confirm_del"] = cid
                    st.rerun()

                if st.session_state.get("grp_confirm_del") == cid:
                    with st.container(border=True):
                        st.warning(
                            f"⚠️ ¿Eliminar el grupo **{cid}**? "
                            "Esta acción no se puede deshacer."
                        )
                        cb1, cb2 = st.columns(2)
                        if cb1.button("🗑️ Sí, eliminar", key=f"grp_del_ok_{cid}",
                                      use_container_width=True, type="primary"):
                            ok, msg = web_eliminar_curso(cid)
                            if ok:
                                _flash_set("success", f"✅ {msg}")
                            else:
                                _flash_set("error", f"❌ {msg}")
                            st.session_state.pop("grp_confirm_del", None)
                            st.session_state.pop("cursos_completo_cache", None)
                            st.rerun()
                        if cb2.button("✖ Cancelar", key=f"grp_del_cancel_{cid}",
                                      use_container_width=True):
                            st.session_state.pop("grp_confirm_del", None)
                            st.rerun()
    else:
        st.info("No hay grupos registrados.")
# ==========================================
# 🧑‍🏫 DIRECCIONES DE GRUPO
# ==========================================
elif opcion == "🧑‍🏫 Direcciones de Grupo":
    st.title("🧑‍🏫 Direcciones de Grupo")
    st.write("Asigne un docente como director de grupo para cada curso y año lectivo.")

    # ── Cargar datos de apoyo ─────────────────────────────────────────────────
    cursos_raw = web_obtener_cursos_completo()   # lista de dicts
    personal   = web_obtener_personal_activo()   # [(id, nombre, rol), ...]

    if not cursos_raw:
        _flash_set("warning", "⚠️ No hay grupos creados. Primero cree grupos en **Gestionar Grupos**.")
        if st.button("➕ Ir a Gestionar Grupos"):
            st.session_state["pagina_activa"] = "📚 Gestionar Grupos"
            st.rerun()
        st.stop()

    if not personal:
        _flash_set("warning", "⚠️ No hay personal registrado. Primero registre docentes en **Registrar Personal**.")
        if st.button("➕ Ir a Registrar Personal"):
            st.session_state["pagina_activa"] = "🆕 Registrar Personal"
            st.rerun()
        st.stop()

    # ── Formulario de asignación ──────────────────────────────────────────────
    st.markdown("### ➕ Asignar director de grupo")

    with st.form("form_dir_grupo", clear_on_submit=True):
        # Listas ordenadas con labels que incluyen el ID único → sin colisiones silenciosas
        opciones_cursos = [
            (f"[{c['id_curso']}] {c['grado']} · Grupo {c['grupo']} · {c['ano']} ({c['jornada']})", c)
            for c in cursos_raw
        ]
        opciones_personal = [
            (f"[{id_p}] {nombre} — {rol}", id_p)
            for id_p, nombre, rol in personal
        ]

        col1, col2 = st.columns(2)
        with col1:
            idx_curso   = st.selectbox("Grupo / Curso*",
                                       range(len(opciones_cursos)),
                                       format_func=lambda i: opciones_cursos[i][0])
        with col2:
            idx_docente = st.selectbox("Director de grupo*",
                                       range(len(opciones_personal)),
                                       format_func=lambda i: opciones_personal[i][0])

        ano_dir = st.number_input("Año lectivo de la asignación*", min_value=2000,
                                  max_value=2100, value=date.today().year, step=1,
                                  help="Puede diferir del año del curso si necesita asignar con anticipación.")

        btn_asignar = st.form_submit_button("💾 Asignar director", use_container_width=True)

    if btn_asignar:
        curso_sel  = opciones_cursos[idx_curso][1]
        id_curso_s = curso_sel["id_curso"]
        id_pers_s  = opciones_personal[idx_docente][1]
        codigo_dg  = web_generar_codigo_direccion_grupo()

        if codigo_dg is None:
            st.error("❌ No se pudo generar el código de asignación. Verifique la conexión.")
        else:
            with st.spinner("Registrando asignación..."):
                ok, msg = web_registrar_direccion_grupo(
                    codigo_dg, id_curso_s, id_pers_s, int(ano_dir)
                )
            if ok:
                st.success(f"✅ {msg}")
                if "dir_grupo_cache" in st.session_state:
                    del st.session_state["dir_grupo_cache"]
            else:
                st.error(f"❌ {msg}")

    # ── Tabla de asignaciones ─────────────────────────────────────────────────
    st.write("---")
    st.markdown("### 📋 Asignaciones registradas")

    if "dir_grupo_cache" not in st.session_state:
        st.session_state.dir_grupo_cache = web_consultar_direcciones_grupo()

    dir_list = st.session_state.dir_grupo_cache

    # Filtro por año
    anos_dir = sorted({d["ano_lectivo"] for d in dir_list}, reverse=True)
    if anos_dir:
        ano_dir_filtro = st.selectbox("Filtrar por año lectivo", anos_dir,
                                      key="dir_filtro_ano")
        dir_filtrado = [d for d in dir_list if d["ano_lectivo"] == ano_dir_filtro]
    else:
        dir_filtrado = dir_list

    if dir_filtrado:
        for item in dir_filtrado:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                c1.markdown(f"**{item['id_curso']}**")
                c2.markdown(f"{item['id_grado']} · Grupo {item['grupo']}")
                c3.markdown(f"🧑‍🏫 {item['nombre_director']}")
                c4.markdown(f"_{item['rol']}_")
                with c5:
                    if st.button("🗑️", key=f"del_dg_{item['id_direccion_grupo']}",
                                 help=f"Eliminar asignación {item['id_direccion_grupo']}"):
                        ok, msg = web_eliminar_direccion_grupo(item["id_direccion_grupo"])
                        if ok:
                            _flash_set("success", f"✅ {msg}")
                            if "dir_grupo_cache" in st.session_state:
                                del st.session_state["dir_grupo_cache"]
                            st.rerun()
                        else:
                            _flash_set("error", f"❌ {msg}")
            st.divider()
        st.caption(f"Total: {len(dir_filtrado)} asignación(es)")
    else:
        st.info("No hay direcciones de grupo registradas para el año seleccionado.")

    if st.button("🔄 Actualizar lista", key="dir_refresh"):
        if "dir_grupo_cache" in st.session_state:
            del st.session_state["dir_grupo_cache"]
        st.rerun()

# ==========================================
# 📖 ASIGNATURAS
# ==========================================
elif opcion == "📖 Asignaturas":
    st.title("📖 Asignaturas")
    st.write("Administre el catálogo de asignaturas que se dictan en la institución.")

    AREAS = [
        "Matemáticas",
        "Lenguaje y Literatura",
        "Ciencias Naturales",
        "Ciencias Sociales",
        "Educación Artística",
        "Educación Física",
        "Tecnología e Informática",
        "Inglés / Lengua Extranjera",
        "Ética y Valores",
        "Religión",
        "Filosofía",
        "Otra",
    ]
    NIVELES_ASG = ["TODOS", "PREESCOLAR", "PRIMARIA", "SECUNDARIA", "MEDIA"]
    NIVEL_ASG_LABEL = {
        "TODOS":      "📚 Todos los niveles",
        "PREESCOLAR": "🌱 Preescolar",
        "PRIMARIA":   "🏫 Primaria",
        "SECUNDARIA": "📗 Básica Secundaria",
        "MEDIA":      "🎓 Media",
    }

    # ── Formulario de creación ────────────────────────────────────────────────
    st.markdown("### ➕ Agregar asignatura")
    with st.form("form_nueva_asignatura", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            asg_nombre = st.text_input("Nombre de la asignatura*",
                                       placeholder="Ej: Matemáticas, Biología, Ed. Física…")
        with col2:
            asg_area = st.selectbox("Área de conocimiento*", AREAS)
        col3, col4 = st.columns(2)
        with col3:
            asg_nivel = st.selectbox(
                "Nivel educativo*",
                NIVELES_ASG,
                format_func=lambda v: NIVEL_ASG_LABEL.get(v, v),
                help="Seleccione en qué nivel se dicta esta asignatura. "
                     "'Todos los niveles' la mostrará siempre."
            )
        with col4:
            asg_desc = st.text_input("Descripción (opcional)",
                                     placeholder="Ej: Incluye álgebra, geometría y estadística")
        btn_asg = st.form_submit_button("💾 Guardar asignatura", use_container_width=True)

    if btn_asg:
        nombre_l = asg_nombre.strip()
        if not nombre_l:
            st.error("❌ El nombre de la asignatura es obligatorio.")
        else:
            with st.spinner("Guardando..."):
                ok, msg = web_registrar_asignatura(nombre_l, asg_area, asg_desc, asg_nivel)
            if ok:
                _flash_set("success", f"✅ {msg}")
                st.session_state.pop("asignaturas_cache", None)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    # ── Catálogo registrado ───────────────────────────────────────────────────
    st.write("---")
    st.markdown("### 📋 Catálogo registrado")

    if "asignaturas_cache" not in st.session_state:
        st.session_state.asignaturas_cache = web_obtener_asignaturas()

    lista_asg = st.session_state.asignaturas_cache

    if lista_asg:
        fc1, fc2 = st.columns(2)
        with fc1:
            nivel_filtro = st.selectbox(
                "Filtrar por nivel",
                ["Todos"] + NIVELES_ASG,
                format_func=lambda v: "Todos los niveles" if v == "Todos"
                                      else NIVEL_ASG_LABEL.get(v, v),
                key="asg_filtro_nivel"
            )
        with fc2:
            area_filtro = st.selectbox(
                "Filtrar por área",
                ["Todas las áreas"] + sorted({a["area_conocimiento"] for a in lista_asg}),
                key="asg_filtro_area"
            )

        filtradas = lista_asg
        if nivel_filtro != "Todos":
            filtradas = [a for a in filtradas if a.get("nivel") == nivel_filtro]
        if area_filtro != "Todas las áreas":
            filtradas = [a for a in filtradas if a["area_conocimiento"] == area_filtro]

        # Limpiar edición huérfana
        ids_filtradas = {a["id_asignatura"] for a in filtradas}
        if st.session_state.get("asg_edit_id") not in ids_filtradas:
            st.session_state.pop("asg_edit_id", None)

        if st.button("🔄 Actualizar catálogo", key="asg_refresh"):
            st.session_state.pop("asignaturas_cache", None)
            st.rerun()

        st.caption(f"Total: {len(filtradas)} asignatura(s)")

        # Cabecera
        hdr = st.columns([3, 3, 2, 4, 1, 1])
        for col, lbl in zip(hdr, ["Nombre", "Área", "Nivel", "Descripción", "", ""]):
            col.markdown(f"**{lbl}**")
        st.divider()

        for asg in filtradas:
            aid = asg["id_asignatura"]

            # ── Modo edición ──────────────────────────────────────────────
            if st.session_state.get("asg_edit_id") == aid:
                with st.container(border=True):
                    st.markdown(f"**✏️ Editando: {aid}**")
                    ea1, ea2 = st.columns(2)
                    with ea1:
                        e_nom = st.text_input("Nombre*", value=asg["nombre"],
                                              key=f"asg_en_{aid}")
                    with ea2:
                        e_area = st.selectbox(
                            "Área*", AREAS,
                            index=AREAS.index(asg["area_conocimiento"])
                                  if asg["area_conocimiento"] in AREAS else 0,
                            key=f"asg_ea_{aid}"
                        )
                    ea3, ea4 = st.columns(2)
                    with ea3:
                        nv = asg.get("nivel", "TODOS")
                        e_nivel = st.selectbox(
                            "Nivel*", NIVELES_ASG,
                            index=NIVELES_ASG.index(nv) if nv in NIVELES_ASG else 0,
                            format_func=lambda v: NIVEL_ASG_LABEL.get(v, v),
                            key=f"asg_eniv_{aid}"
                        )
                    with ea4:
                        e_desc = st.text_input("Descripción", value=asg["descripcion"] or "",
                                               key=f"asg_ed_{aid}")
                    eb1, eb2 = st.columns(2)
                    if eb1.button("💾 Guardar", key=f"asg_save_{aid}",
                                  use_container_width=True, type="primary"):
                        if not e_nom.strip():
                            st.error("❌ El nombre es obligatorio.")
                        else:
                            ok, msg = web_actualizar_asignatura(
                                aid, e_nom, e_area, e_desc, e_nivel
                            )
                            if ok:
                                _flash_set("success", f"✅ {msg}")
                            else:
                                _flash_set("error", f"❌ {msg}")
                            st.session_state.pop("asg_edit_id", None)
                            st.session_state.pop("asignaturas_cache", None)
                            st.rerun()
                    if eb2.button("✖ Cancelar", key=f"asg_cancel_{aid}",
                                  use_container_width=True):
                        st.session_state.pop("asg_edit_id", None)
                        st.rerun()
            else:
                # ── Fila normal ───────────────────────────────────────────
                row = st.columns([3, 3, 2, 4, 1, 1])
                row[0].markdown(f"**{asg['nombre']}**")
                row[1].markdown(f"_{asg['area_conocimiento']}_")
                row[2].markdown(NIVEL_ASG_LABEL.get(asg.get("nivel","TODOS"), "—"))
                row[3].markdown(asg["descripcion"] or "")
                if row[4].button("✏️", key=f"asg_edit_{aid}", help="Editar"):
                    st.session_state["asg_edit_id"] = aid
                    st.rerun()
                if row[5].button("🗑️", key=f"del_asg_{aid}", help="Eliminar"):
                    ok, msg = web_eliminar_asignatura(aid)
                    if ok:
                        _flash_set("success", f"✅ {msg}")
                        st.session_state.pop("asignaturas_cache", None)
                        st.rerun()
                    else:
                        _flash_set("error", f"❌ {msg}")
            st.divider()
    else:
        st.info("No hay asignaturas registradas. Agregue la primera usando el formulario de arriba.")
        if st.button("🔄 Actualizar catálogo", key="asg_refresh"):
            st.session_state.pop("asignaturas_cache", None)
            st.rerun()

# ==========================================
# 📋 PLAN DE ESTUDIO
# ==========================================
elif opcion == "📋 Plan de Estudio":
    st.title("📋 Plan de Estudio")
    st.write("Defina qué asignaturas se dictan en cada grado y cuántas horas semanales.")

    grados = web_obtener_grados()
    if not grados:
        st.error("❌ No se pudieron cargar los grados. Verifique la conexión.")
        st.stop()

    asignaturas_todas = web_obtener_asignaturas()
    if not asignaturas_todas:
        _flash_set("warning", "⚠️ No hay asignaturas en el catálogo. Primero agréguelas en **Asignaturas**.")
        if st.button("➕ Ir a Asignaturas"):
            st.session_state["pagina_activa"] = "📖 Asignaturas"
            st.rerun()
        st.stop()

    # Selector de grado (persistente)
    mapa_grados = {f"{ng}": ig for ig, ng in grados}
    sel_grado_label = st.selectbox("Seleccione el grado a administrar",
                                   list(mapa_grados.keys()), key="pe_sel_grado")
    id_grado_sel = mapa_grados[sel_grado_label]

    st.write("---")

    # ── Plan actual del grado ──────────────────────────────────────────────────
    st.markdown(f"### 📚 Plan de **{sel_grado_label}**")

    cache_key = f"plan_cache_{id_grado_sel}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = web_obtener_plan_estudio(id_grado_sel)

    plan_actual = st.session_state[cache_key]

    if plan_actual:
        total_horas = sum(p["horas_semana"] for p in plan_actual)
        col_h1, col_h2 = st.columns(2)
        col_h1.metric("Asignaturas en el plan", len(plan_actual))
        col_h2.metric("Total horas / semana", total_horas)
        st.write("")

        # Limpiar edición huérfana
        ids_plan = {item["id_plan"] for item in plan_actual}
        if st.session_state.get("pe_edit_id") not in ids_plan:
            st.session_state.pop("pe_edit_id", None)

        # Cabecera
        hdr_pe = st.columns([4, 3, 2, 1, 1])
        for col, lbl in zip(hdr_pe, ["Asignatura", "Área", "Horas/sem", "", ""]):
            col.markdown(f"**{lbl}**")
        st.divider()

        for item in plan_actual:
            iid = item["id_plan"]

            # ── Modo edición de horas ─────────────────────────────────────
            if st.session_state.get("pe_edit_id") == iid:
                with st.container(border=True):
                    st.markdown(f"**✏️ Editar horas — {item['nombre_asignatura']}**")
                    pe1, pe2 = st.columns([2, 3])
                    nuevas_horas = pe1.number_input(
                        "Horas por semana*",
                        min_value=1, max_value=40,
                        value=item["horas_semana"], step=1,
                        key=f"pe_h_{iid}"
                    )
                    pb1, pb2 = st.columns(2)
                    if pb1.button("💾 Guardar", key=f"pe_save_{iid}",
                                  use_container_width=True, type="primary"):
                        ok, msg = web_actualizar_horas_plan(iid, nuevas_horas)
                        if ok:
                            _flash_set("success", f"✅ {msg}")
                        else:
                            _flash_set("error", f"❌ {msg}")
                        st.session_state.pop("pe_edit_id", None)
                        st.session_state.pop(cache_key, None)
                        st.rerun()
                    if pb2.button("✖ Cancelar", key=f"pe_cancel_{iid}",
                                  use_container_width=True):
                        st.session_state.pop("pe_edit_id", None)
                        st.rerun()
            else:
                # ── Fila normal ───────────────────────────────────────────
                row_pe = st.columns([4, 3, 2, 1, 1])
                row_pe[0].markdown(f"**{item['nombre_asignatura']}**")
                row_pe[1].markdown(f"_{item['area']}_")
                row_pe[2].markdown(f"⏱️ {item['horas_semana']} h/sem")
                if row_pe[3].button("✏️", key=f"pe_edit_{iid}",
                                    help="Editar horas"):
                    st.session_state["pe_edit_id"] = iid
                    st.rerun()
                if row_pe[4].button("🗑️", key=f"del_pe_{iid}",
                                    help="Retirar del plan"):
                    ok, msg = web_eliminar_plan_estudio(iid)
                    if ok:
                        _flash_set("success", f"✅ {msg}")
                        st.session_state.pop(cache_key, None)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            st.divider()
    else:
        st.info("Este grado no tiene asignaturas en el plan de estudio todavía.")

    # ── Agregar asignatura al plan ─────────────────────────────────────────────
    st.markdown("### ➕ Agregar asignatura al plan")

    disponibles = web_obtener_asignaturas_sin_asignar(id_grado_sel)
    if not disponibles:
        st.info("✅ Todas las asignaturas compatibles ya están en el plan de este grado.")
    else:
        opciones_disp = [
            (f"[{id_a}] {nom} — {area}  ({niv})", id_a)
            for id_a, nom, area, niv in disponibles
        ]
        with st.form(f"form_agregar_pe_{id_grado_sel}", clear_on_submit=True):
            idx_asg = st.selectbox(
                "Asignatura*",
                range(len(opciones_disp)),
                format_func=lambda i: opciones_disp[i][0]
            )
            horas = st.number_input("Horas por semana*", min_value=1, max_value=40,
                                    value=4, step=1)
            btn_pe = st.form_submit_button("💾 Agregar al plan", use_container_width=True)

        if btn_pe:
            id_asg_sel = opciones_disp[idx_asg][1]
            with st.spinner("Guardando..."):
                ok, msg = web_registrar_plan_estudio(id_grado_sel, id_asg_sel, horas)
            if ok:
                _flash_set("success", f"✅ {msg}")
                st.session_state.pop(cache_key, None)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

# ==========================================
# 👩‍🏫 ASIGNACIÓN DOCENTE
# ==========================================
elif opcion == "👩‍🏫 Asignación Docente":
    st.title("👩‍🏫 Asignación Docente")
    st.write("Asigne o retire docentes de cada asignatura por grupo y año lectivo.")

    personal = web_obtener_personal_activo()
    cursos_raw = web_obtener_cursos_completo()

    if not cursos_raw:
        _flash_set("warning", "⚠️ No hay grupos creados. Cree grupos primero en **Gestionar Grupos**.")
        if st.button("➕ Ir a Gestionar Grupos", key="ad_ir_grupos"):
            st.session_state["pagina_activa"] = "📚 Gestionar Grupos"
            st.rerun()
        st.stop()

    if not personal:
        _flash_set("warning", "⚠️ No hay personal registrado. Registre docentes primero.")
        if st.button("➕ Ir a Registrar Personal", key="ad_ir_personal"):
            st.session_state["pagina_activa"] = "🆕 Registrar Personal"
            st.rerun()
        st.stop()

    # ── Filtros de navegación ─────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ano_ad = st.number_input("Año lectivo", min_value=2000, max_value=2100,
                                 value=date.today().year, step=1, key="ad_ano")
    with col_f2:
        opciones_cursos_ad = [
            (f"[{c['id_curso']}] {c['grado']} · Grupo {c['grupo']} ({c['jornada']})", c)
            for c in cursos_raw
        ]
        idx_curso_ad = st.selectbox(
            "Grupo / Curso",
            range(len(opciones_cursos_ad)),
            format_func=lambda i: opciones_cursos_ad[i][0],
            key="ad_sel_curso"
        )

    curso_ad   = opciones_cursos_ad[idx_curso_ad][1]
    id_curso_ad = curso_ad["id_curso"]
    id_grado_ad = curso_ad["id_grado"]

    st.write("---")

    # ── Asignaciones actuales ─────────────────────────────────────────────────
    st.markdown(f"### 📋 Asignaciones — {curso_ad['grado']} · Grupo {curso_ad['grupo']} · {int(ano_ad)}")

    cache_ad = f"asig_doc_cache_{id_curso_ad}_{int(ano_ad)}"
    if cache_ad not in st.session_state:
        st.session_state[cache_ad] = web_obtener_asignaciones_docente(
            id_curso=id_curso_ad, ano_lectivo=int(ano_ad)
        )

    asigs_actuales = st.session_state[cache_ad]

    if asigs_actuales:
        total_horas_ad = 0
        plan_grado = {p["id_asignatura"]: p["horas_semana"]
                      for p in web_obtener_plan_estudio(id_grado_ad)}
        for item in asigs_actuales:
            horas_plan = plan_grado.get(item["id_asignatura"], "—")
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 1])
                c1.markdown(f"**{item['nombre_asignatura']}**")
                c2.markdown(f"_{item['area']}_")
                c3.markdown(f"🧑‍🏫 {item['nombre_docente']}")
                c4.markdown(f"{horas_plan} h/sem" if horas_plan != "—" else "")
                with c5:
                    if st.button("🗑️", key=f"del_ad_{item['id_asignacion']}",
                                 help="Retirar asignación"):
                        ok, msg = web_eliminar_asignacion_docente(item["id_asignacion"])
                        if ok:
                            _flash_set("success", f"✅ {msg}")
                            if cache_ad in st.session_state:
                                del st.session_state[cache_ad]
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            st.divider()
        st.caption(f"Total: {len(asigs_actuales)} asignación(es) en este grupo")
    else:
        st.info("Este grupo no tiene docentes asignados para el año seleccionado.")

    # ── Formulario de asignación ──────────────────────────────────────────────
    st.markdown("### ➕ Asignar docente")

    # Asignaturas del plan de estudio del grado, sin las ya asignadas en este curso/año
    plan_grado_lista = web_obtener_plan_estudio(id_grado_ad)
    ids_ya_asignados = {a["id_asignatura"] for a in asigs_actuales}
    asg_disponibles = [(p["id_asignatura"], p["nombre_asignatura"], p["area"])
                       for p in plan_grado_lista
                       if p["id_asignatura"] not in ids_ya_asignados]

    if not asg_disponibles:
        st.info("✅ Todos los docentes del plan de estudio de este grado ya están asignados "
                "en este grupo. Retire alguno para reasignarlo, o revise el Plan de Estudio.")
    else:
        opciones_asg_ad = [
            (f"[{id_a}] {nom} — {area}", id_a)
            for id_a, nom, area in asg_disponibles
        ]
        opciones_pers_ad = [
            (f"[{id_p}] {nom} — {rol}", id_p)
            for id_p, nom, rol in personal
        ]
        with st.form(f"form_asig_doc_{id_curso_ad}_{int(ano_ad)}", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                idx_asg_ad = st.selectbox(
                    "Asignatura*",
                    range(len(opciones_asg_ad)),
                    format_func=lambda i: opciones_asg_ad[i][0]
                )
            with col_a2:
                idx_pers_ad = st.selectbox(
                    "Docente*",
                    range(len(opciones_pers_ad)),
                    format_func=lambda i: opciones_pers_ad[i][0]
                )
            btn_ad = st.form_submit_button("💾 Asignar docente", use_container_width=True)

        if btn_ad:
            id_asg_ad  = opciones_asg_ad[idx_asg_ad][1]
            id_pers_ad = opciones_pers_ad[idx_pers_ad][1]
            with st.spinner("Registrando asignación..."):
                ok, msg = web_registrar_asignacion_docente(
                    id_curso_ad, id_pers_ad, id_asg_ad, int(ano_ad)
                )
            if ok:
                _flash_set("success", f"✅ {msg}")
                if cache_ad in st.session_state:
                    del st.session_state[cache_ad]
                st.rerun()
            else:
                st.error(f"❌ {msg}")


# ==========================================
# 📚 GRADOS
# ==========================================
elif opcion == "📚 Grados":
    st.title("📚 Gestión de Grados")
    st.write("Cree, edite o elimine los grados de su institución. Los niveles determinan cómo se etiquetan los boletines.")

    NIVEL_LABELS = {
        "PREESCOLAR": "🟡 Preescolar",
        "PRIMARIA":   "🟢 Primaria",
        "SECUNDARIA": "🔵 Básica Secundaria",
        "MEDIA":      "🟣 Media",
    }

    # ── Agregar nuevo grado ───────────────────────────────────────────────────
    st.markdown("### ➕ Agregar grado")
    with st.form("form_nuevo_grado", clear_on_submit=True):
        ng1, ng2, ng3 = st.columns([4, 3, 2])
        with ng1:
            nuevo_nombre = st.text_input("Nombre del grado*",
                                         placeholder="Ej: Maternal, Prejardín, Jardín, Transición…")
        with ng2:
            nuevo_nivel = st.selectbox("Nivel*",
                                       options=["PREESCOLAR", "PRIMARIA", "SECUNDARIA", "MEDIA"],
                                       format_func=lambda v: {"PREESCOLAR": "Preescolar", "PRIMARIA": "Primaria",
                                                              "SECUNDARIA": "Básica Secundaria", "MEDIA": "Media"}.get(v, v))
        with ng3:
            nuevo_orden = st.number_input("Orden en menús", min_value=0, max_value=99,
                                           value=0,
                                           help="Número menor aparece primero en los selectores.")
        btn_nuevo_g = st.form_submit_button("➕ Registrar grado", use_container_width=True, type="primary")

    if btn_nuevo_g:
        ok_g, msg_g, _ = web_registrar_grado(nuevo_nombre, nuevo_nivel, nuevo_orden)
        if ok_g:
            _flash_set("success", f"✅ {msg_g}")
            for k in [k for k in st.session_state if "grado" in k.lower() or k == "grados_cache"]:
                del st.session_state[k]
            st.rerun()
        else:
            st.error(f"❌ {msg_g}")

    st.write("---")

    # ── Tabla de grados existentes ────────────────────────────────────────────
    st.markdown("### 📋 Grados registrados")
    grados_full = web_obtener_grados_completo()
    if not grados_full:
        st.warning("No hay grados registrados.")
    else:
        # Cabecera
        hg0, hg1, hg2, hg3, hg4 = st.columns([1, 3, 3, 2, 2])
        for lbl, col in zip(["ID","Nombre","Nivel","Orden","Acciones"],
                             [hg0, hg1, hg2, hg3, hg4]):
            col.markdown(f"**{lbl}**")
        st.write("---")

        for g in grados_full:
            c0, c1, c2, c3, c4 = st.columns([1, 3, 3, 2, 2])
            c0.code(g["id_grado"], language=None)
            c1.write(g["nombre_grado"])
            c2.write(NIVEL_LABELS.get(g["nivel"], g["nivel"]))
            c3.write(str(g["orden"]))

            with c4:
                col_ed, col_el = st.columns(2)
                with col_ed:
                    if st.button("✏️", key=f"ed_g_{g['id_grado']}",
                                 help="Editar grado", use_container_width=True):
                        st.session_state["grado_editar"] = g
                        st.rerun()
                with col_el:
                    if st.button("🗑️", key=f"del_g_{g['id_grado']}",
                                 help="Eliminar grado", use_container_width=True):
                        ok_del, msg_del = web_eliminar_grado(g["id_grado"])
                        if ok_del:
                            _flash_set("success", f"✅ {msg_del}")
                            for k in [k for k in st.session_state if "grado" in k.lower() or k == "grados_cache"]:
                                del st.session_state[k]
                            st.rerun()
                        else:
                            st.error(f"❌ {msg_del}")

    # ── Panel de edición ──────────────────────────────────────────────────────
    if "grado_editar" in st.session_state:
        ge = st.session_state["grado_editar"]
        st.write("---")
        st.markdown(f"### ✏️ Editar: {ge['nombre_grado']}")
        with st.form("form_editar_grado"):
            ee1, ee2, ee3 = st.columns([4, 3, 2])
            with ee1:
                e_nombre = st.text_input("Nombre*", value=ge["nombre_grado"])
            with ee2:
                niveles = ["PREESCOLAR", "PRIMARIA", "SECUNDARIA", "MEDIA"]
                e_nivel  = st.selectbox("Nivel*", options=niveles,
                                        format_func=lambda v: {"PREESCOLAR": "Preescolar", "PRIMARIA": "Primaria",
                                                               "SECUNDARIA": "Básica Secundaria", "MEDIA": "Media"}.get(v, v),
                                        index=niveles.index(ge["nivel"]) if ge["nivel"] in niveles else 0)
            with ee3:
                e_orden = st.number_input("Orden", min_value=0, max_value=99, value=int(ge["orden"]))
            ec1, ec2 = st.columns(2)
            with ec1:
                btn_guardar_g = st.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary")
            with ec2:
                btn_cancelar_g = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if btn_guardar_g:
            ok_u, msg_u = web_actualizar_grado(ge["id_grado"], e_nombre, e_nivel, e_orden)
            if ok_u:
                _flash_set("success", f"✅ {msg_u}")
                del st.session_state["grado_editar"]
                for k in [k for k in st.session_state if "grado" in k.lower() or k == "grados_cache"]:
                    del st.session_state[k]
                st.rerun()
            else:
                _flash_set("error", f"❌ {msg_u}")

        if btn_cancelar_g:
            del st.session_state["grado_editar"]
            st.rerun()

    st.write("---")
    st.info("💡 **Tip:** El campo **Nivel** determina el orden de aparición en la pantalla y cómo se llama la columna izquierda del boletín. "
            "Preescolar → *Dimensión* · Primaria / Básica Secundaria / Media → *Asignatura*.")


# ==========================================
# 🏫 SEDES
# ==========================================
elif opcion == "🏫 Sedes":
    mostrar_modulo_sedes()
    
  

# ==========================================
# 📅 PERÍODOS ACADÉMICOS
# ==========================================
elif opcion == "📅 Períodos":
    from datetime import date as _dt
    st.title("📅 Períodos Académicos")
    st.write("Configure los períodos del año lectivo: nombre, fechas y peso porcentual.")

    # ── Año de trabajo ────────────────────────────────────────────────────────
    col_ano, _ = st.columns([2, 5])
    with col_ano:
        ano_per = st.number_input(
            "Año lectivo", min_value=2020, max_value=2050,
            value=_dt.today().year, step=1, key="per_ano"
        )

    # ── Cargar períodos existentes ────────────────────────────────────────────
    cache_key = f"periodos_cache_{ano_per}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = web_obtener_periodos(ano_per)
    existentes = {p["numero"]: p for p in st.session_state[cache_key]}

    st.write("---")
    st.markdown("### ⚙️ Configuración de períodos")

    # ── Número de períodos ────────────────────────────────────────────────────
    n_actuales = len(existentes) if existentes else 4
    n_per = st.radio(
        "Número de períodos para este año",
        options=[3, 4],
        index=0 if n_actuales == 3 else 1,
        horizontal=True,
        key="per_n"
    )

    st.markdown(
        "<small>Los porcentajes deben sumar exactamente **100 %**.</small>",
        unsafe_allow_html=True
    )

    TIPOS_PERIODO = {
        1: ("Primer Período",   f"01/02/{ano_per}", f"31/03/{ano_per}", 25.0),
        2: ("Segundo Período",  f"01/04/{ano_per}", f"30/06/{ano_per}", 25.0),
        3: ("Tercer Período",   f"15/07/{ano_per}", f"30/09/{ano_per}", 25.0),
        4: ("Cuarto Período",   f"01/10/{ano_per}", f"30/11/{ano_per}", 25.0),
    }

    # ── Formulario con un campo por período ──────────────────────────────────
    with st.form("form_periodos"):
        datos_form = []
        suma_display = 0.0
        for num in range(1, n_per + 1):
            prev = existentes.get(num, {})
            defts = TIPOS_PERIODO[num]
            st.markdown(f"#### Período {num}")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
            with c1:
                nombre_p = st.text_input(
                    "Nombre", value=prev.get("nombre", defts[0]),
                    key=f"per_nom_{num}"
                )
            with c2:
                fi_def = prev.get("fecha_inicio") or _dt.today().replace(month=2, day=1)
                fi = st.date_input("Inicio", value=fi_def, key=f"per_ini_{num}")
            with c3:
                ff_def = prev.get("fecha_fin") or _dt.today().replace(month=3, day=31)
                ff = st.date_input("Fin",   value=ff_def, key=f"per_fin_{num}")
            with c4:
                pct = st.number_input(
                    "% peso", min_value=0.01, max_value=100.0, step=0.5,
                    value=float(prev.get("porcentaje", defts[3])),
                    key=f"per_pct_{num}"
                )
            datos_form.append({
                "numero": num, "nombre": nombre_p,
                "fecha_inicio": fi, "fecha_fin": ff, "porcentaje": pct
            })
            suma_display += pct

        # Indicador visual de suma
        color_suma = "green" if abs(suma_display - 100) < 0.01 else "red"
        st.markdown(
            f"<p style='font-weight:700;color:{color_suma};margin-top:8px'>"
            f"Suma total: {suma_display:.2f} % "
            f"({'✅ OK' if color_suma == 'green' else '❌ Debe ser 100 %'})</p>",
            unsafe_allow_html=True
        )

        btn_guardar_per = st.form_submit_button(
            "💾 Guardar períodos", use_container_width=True,
            type="primary"
        )

    if btn_guardar_per:
        with st.spinner("Guardando…"):
            ok, msg = web_guardar_periodos(ano_per, datos_form)
        if ok:
            _flash_set("success", f"✅ {msg}")
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()
        else:
            st.error(f"❌ {msg}")

    # ── Resumen actual ────────────────────────────────────────────────────────
    if existentes:
        st.write("---")
        st.markdown(f"### 📋 Períodos guardados — {ano_per}")
        cols_h = st.columns([1, 3, 2, 2, 1.5])
        for lbl, col in zip(["N°", "Nombre", "Inicio", "Fin", "Peso %"], cols_h):
            col.markdown(f"**{lbl}**")
        for p in sorted(existentes.values(), key=lambda x: x["numero"]):
            row = st.columns([1, 3, 2, 2, 1.5])
            row[0].write(p["numero"])
            row[1].write(p["nombre"])
            row[2].write(str(p["fecha_inicio"]) if p["fecha_inicio"] else "—")
            row[3].write(str(p["fecha_fin"])    if p["fecha_fin"]    else "—")
            row[4].write(f"{float(p['porcentaje']):.1f} %")
        total_g = sum(float(p["porcentaje"]) for p in existentes.values())
        st.markdown(
            f"<p style='font-weight:700;color:{'green' if abs(total_g-100)<0.01 else 'red'}'>"
            f"Total: {total_g:.1f} %</p>",
            unsafe_allow_html=True
        )


# ==========================================
# 📝 INDICADORES DE DESEMPEÑO
# ==========================================
elif opcion == "📝 Indicadores":
    from datetime import date as _dt2
    st.title("📝 Indicadores de Desempeño")
    st.write(
        "Defina los aprendizajes o indicadores esperados por grado, "
        "asignatura y período."
    )

    # ── Filtros ───────────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns([1.5, 2, 2, 1.5])

    with f1:
        ano_ind = st.number_input(
            "Año lectivo", min_value=2020, max_value=2050,
            value=_dt2.today().year, step=1, key="ind_ano"
        )

    # Grados
    if "grados_cache" not in st.session_state:
        st.session_state.grados_cache = web_obtener_grados()
    grados_list = st.session_state.grados_cache  # [(id_grado, nombre_grado)]
    if not grados_list:
        st.warning("No hay grados registrados.")
        st.stop()
    with f2:
        idx_grado = st.selectbox(
            "Grado", options=range(len(grados_list)),
            format_func=lambda i: grados_list[i][1],
            key="ind_grado"
        )
    id_grado_sel = grados_list[idx_grado][0]

    # Asignaturas
    if "asig_cache_ind" not in st.session_state:
        st.session_state.asig_cache_ind = web_obtener_asignaturas()
    asig_list = st.session_state.asig_cache_ind  # [{'id_asignatura':..,'nombre':..}]
    if not asig_list:
        st.warning("No hay asignaturas registradas.")
        st.stop()
    with f3:
        idx_asig = st.selectbox(
            "Asignatura", options=range(len(asig_list)),
            format_func=lambda i: asig_list[i]["nombre"],
            key="ind_asig"
        )
    id_asig_sel = asig_list[idx_asig]["id_asignatura"]

    # Períodos disponibles para el año
    periodos_disp = web_obtener_periodos(ano_ind)
    if not periodos_disp:
        st.warning(
            f"No hay períodos configurados para {ano_ind}. "
            "Vaya a **Académico → Períodos** y configúrelos primero."
        )
        st.stop()
    with f4:
        opciones_per = [(p["numero"], p["nombre"]) for p in periodos_disp]
        idx_per = st.selectbox(
            "Período", options=range(len(opciones_per)),
            format_func=lambda i: opciones_per[i][1],
            key="ind_per"
        )
    num_per_sel = opciones_per[idx_per][0]

    st.write("---")

    # ── Formulario: nuevo indicador ───────────────────────────────────────────
    st.markdown("### ➕ Agregar indicador")
    with st.form("form_nuevo_ind", clear_on_submit=True):
        desc_nueva = st.text_area(
            "Descripción del indicador / aprendizaje*",
            placeholder="Ej: Identifica y describe las características de los seres vivos…",
            height=90
        )
        tipo_nuevo = st.selectbox(
            "Tipo", ["Cognitivo", "Procedimental", "Actitudinal"],
            help="Cognitivo = saber | Procedimental = hacer | Actitudinal = ser"
        )
        btn_add_ind = st.form_submit_button("💾 Agregar", use_container_width=True)

    if btn_add_ind:
        if not desc_nueva.strip():
            st.error("❌ La descripción es obligatoria.")
        else:
            ok, msg, _ = web_registrar_indicador(
                ano_ind, id_grado_sel, id_asig_sel,
                num_per_sel, desc_nueva, tipo_nuevo
            )
            if ok:
                st.success(f"✅ {msg}")
                cache_i = f"ind_cache_{ano_ind}_{id_grado_sel}_{id_asig_sel}_{num_per_sel}"
                if cache_i in st.session_state:
                    del st.session_state[cache_i]
            else:
                st.error(f"❌ {msg}")

    st.write("---")

    # ── Lista de indicadores ──────────────────────────────────────────────────
    st.markdown(
        f"### 📋 Indicadores — {grados_list[idx_grado][1]} · "
        f"{asig_list[idx_asig]['nombre']} · {opciones_per[idx_per][1]}"
    )

    cache_i = f"ind_cache_{ano_ind}_{id_grado_sel}_{id_asig_sel}_{num_per_sel}"
    if cache_i not in st.session_state:
        st.session_state[cache_i] = web_obtener_indicadores(
            ano_ind, id_grado_sel, id_asig_sel, num_per_sel
        )
    indicadores = st.session_state[cache_i]

    TIPO_COLOR = {
        "Cognitivo":      "#dbeafe",
        "Procedimental":  "#d1fae5",
        "Actitudinal":    "#fef3c7",
    }
    TIPO_TEXTO = {
        "Cognitivo":      "#1e40af",
        "Procedimental":  "#065f46",
        "Actitudinal":    "#92400e",
    }

    if not indicadores:
        st.info("No hay indicadores para esta combinación. Agregue el primero arriba.")
    else:
        for ind in indicadores:
            iid      = ind["id_indicador"]
            edit_key = f"ind_edit_{iid}"
            bg       = TIPO_COLOR.get(ind["tipo"], "#f3f4f6")
            fg       = TIPO_TEXTO.get(ind["tipo"], "#111827")

            with st.container():
                c1, c2, c3 = st.columns([7, 1, 1])
                with c1:
                    st.markdown(
                        f"<div style='background:{bg};border-radius:10px;padding:10px 14px;'>"
                        f"<span style='font-size:10px;font-weight:700;color:{fg};"
                        f"text-transform:uppercase;letter-spacing:1px'>{ind['tipo']}</span><br>"
                        f"<span style='color:#1a202c'>{ind['descripcion']}</span>"
                        f"<br><small style='color:#9ca3af'>{iid}</small></div>",
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("✏️", key=f"ied_{iid}", help="Editar"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"idd_{iid}", help="Eliminar"):
                        ok2, msg2 = web_eliminar_indicador(iid)
                        if ok2:
                            _flash_set("success", f"✅ {msg2}")
                            if cache_i in st.session_state:
                                del st.session_state[cache_i]
                            st.rerun()
                        else:
                            st.error(f"❌ {msg2}")

                if st.session_state.get(edit_key, False):
                    with st.form(f"form_edit_ind_{iid}"):
                        e_desc = st.text_area("Descripción*", value=ind["descripcion"], height=80)
                        e_tipo = st.selectbox(
                            "Tipo",
                            ["Cognitivo", "Procedimental", "Actitudinal"],
                            index=["Cognitivo", "Procedimental", "Actitudinal"].index(ind["tipo"])
                        )
                        cg, cc = st.columns(2)
                        with cg:
                            btn_eg = st.form_submit_button("💾 Guardar", use_container_width=True)
                        with cc:
                            btn_ec = st.form_submit_button("✖ Cancelar", use_container_width=True)

                    if btn_eg:
                        if not e_desc.strip():
                            st.error("❌ La descripción no puede estar vacía.")
                        else:
                            ok3, msg3 = web_actualizar_indicador(iid, e_desc, e_tipo)
                            if ok3:
                                _flash_set("success", f"✅ {msg3}")
                                st.session_state[edit_key] = False
                                if cache_i in st.session_state:
                                    del st.session_state[cache_i]
                                st.rerun()
                            else:
                                _flash_set("error", f"❌ {msg3}")
                    if btn_ec:
                        st.session_state[edit_key] = False
                        st.rerun()

            st.divider()

        st.caption(f"Total: {len(indicadores)} indicador(es)")

    if st.button("🔄 Actualizar", key="ind_refresh"):
        if cache_i in st.session_state:
            del st.session_state[cache_i]
        st.rerun()


# ==========================================
# ⚖️ ESCALA DE VALORACIÓN
# ==========================================
elif opcion == "⚖️ Escala de Valoración":
    st.title("⚖️ Escala de Valoración")
    st.write("Configure los rangos numéricos que definen cada nivel de desempeño.")

    if "escala_cache" not in st.session_state:
        st.session_state.escala_cache = web_obtener_escala()
    escala = st.session_state.escala_cache

    # Colores visuales por nivel
    COLORES_NIVEL = {
        "BAJO":     ("#fee2e2", "#991b1b"),
        "BASICO":   ("#fef3c7", "#92400e"),
        "ALTO":     ("#d1fae5", "#065f46"),
        "SUPERIOR": ("#dbeafe", "#1e40af"),
    }

    # Vista previa de la escala actual
    if escala:
        st.markdown("### 📋 Escala actual")
        cols_h = st.columns([2, 3, 1.5, 1.5, 4])
        for lbl in ["Nivel", "Nombre", "Mín", "Máx", "Descripción"]:
            cols_h.pop(0).markdown(f"**{lbl}**")
        for n in escala:
            bg, fg = COLORES_NIVEL.get(n["id_nivel"], ("#f3f4f6", "#111827"))
            row = st.columns([2, 3, 1.5, 1.5, 4])
            row[0].markdown(
                f"<span style='background:{bg};color:{fg};padding:3px 10px;"
                f"border-radius:12px;font-weight:700;font-size:12px'>{n['id_nivel']}</span>",
                unsafe_allow_html=True
            )
            row[1].write(n["nombre"])
            row[2].write(f"{float(n['valor_min']):.2f}")
            row[3].write(f"{float(n['valor_max']):.2f}")
            row[4].write(n.get("descripcion") or "—")

    st.write("---")
    st.markdown("### ✏️ Editar rangos")
    st.info(
        "Los rangos no deben solaparse. "
        "Ejemplo típico: Bajo 0–2.99 · Básico 3.00–3.89 · Alto 3.90–4.59 · Superior 4.60–5.00"
    )

    if not escala:
        st.warning("No hay niveles de valoración configurados en la base de datos.")
    else:
        with st.form("form_escala"):
            nuevos = []
            for n in escala:
                bg, fg = COLORES_NIVEL.get(n["id_nivel"], ("#f3f4f6", "#111827"))
                st.markdown(
                    f"<div style='background:{bg};color:{fg};display:inline-block;"
                    f"padding:3px 12px;border-radius:12px;font-weight:700;"
                    f"margin-bottom:6px'>{n['nombre']}</div>",
                    unsafe_allow_html=True
                )
                c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 4])
                with c1:
                    e_nom = st.text_input("Nombre", value=n["nombre"],
                                          key=f"ev_nom_{n['id_nivel']}")
                with c2:
                    e_min = st.number_input("Mínimo", value=float(n["valor_min"]),
                                            min_value=0.0, max_value=9.99, step=0.01,
                                            format="%.2f", key=f"ev_min_{n['id_nivel']}")
                with c3:
                    e_max = st.number_input("Máximo", value=float(n["valor_max"]),
                                            min_value=0.01, max_value=10.0, step=0.01,
                                            format="%.2f", key=f"ev_max_{n['id_nivel']}")
                with c4:
                    e_desc = st.text_input("Descripción", value=n.get("descripcion") or "",
                                           key=f"ev_desc_{n['id_nivel']}")
                nuevos.append({
                    "id_nivel": n["id_nivel"], "nombre": e_nom,
                    "valor_min": e_min, "valor_max": e_max, "descripcion": e_desc
                })

            btn_esc = st.form_submit_button("💾 Guardar escala", use_container_width=True,
                                             type="primary")

        if btn_esc:
            ok, msg = web_guardar_escala(nuevos)
            if ok:
                _flash_set("success", f"✅ {msg}")
                if "escala_cache" in st.session_state:
                    del st.session_state["escala_cache"]
                st.rerun()
            else:
                st.error(f"❌ {msg}")


# ==========================================
# 📊 NOTAS — INGRESO DE CALIFICACIONES
# ==========================================
elif opcion == "📊 Notas":
    from datetime import date as _dt3
    st.title("📊 Ingreso de Calificaciones")
    st.write("Seleccione el curso, período y asignatura para registrar las notas.")

    # ── Filtros de selección ──────────────────────────────────────────────────
    fa, fb, fc, fd = st.columns([2, 2, 2, 1.5])

    # Año lectivo
    with fa:
        ano_notas = st.number_input(
            "Año lectivo", min_value=2020, max_value=2050,
            value=_dt3.today().year, step=1, key="notas_ano"
        )

    # Curso (filtrado por año)
    if "cursos_completo_cache" not in st.session_state:
        st.session_state.cursos_completo_cache = web_obtener_cursos_completo()
    cursos_todos = st.session_state.cursos_completo_cache
    cursos_ano   = [c for c in cursos_todos if c["ano"] == ano_notas]

    if not cursos_ano:
        st.warning(f"No hay cursos registrados para {ano_notas}.")
        st.stop()

    with fb:
        idx_curso_n = st.selectbox(
            "Curso / Grupo",
            options=range(len(cursos_ano)),
            format_func=lambda i: f"{cursos_ano[i]['grado']} — Grupo {cursos_ano[i]['grupo']}",
            key="notas_curso"
        )
    curso_sel    = cursos_ano[idx_curso_n]
    id_curso_sel = curso_sel["id_curso"]
    id_grado_n   = curso_sel.get("id_grado") or ""  # puede no venir; usamos plan_estudio

    # Períodos
    periodos_n = web_obtener_periodos(ano_notas)
    if not periodos_n:
        st.warning(f"No hay períodos configurados para {ano_notas}. "
                   "Configure primero en Académico → Períodos.")
        st.stop()
    with fc:
        idx_per_n = st.selectbox(
            "Período",
            options=range(len(periodos_n)),
            format_func=lambda i: periodos_n[i]["nombre"],
            key="notas_per"
        )
    periodo_sel    = periodos_n[idx_per_n]
    num_periodo_n  = periodo_sel["numero"]

    # Asignaturas del grado (desde plan de estudio)
    # Obtenemos el id_grado del curso seleccionado de la tabla cursos
    cache_grado_key = f"grado_de_curso_{id_curso_sel}"
    if cache_grado_key not in st.session_state:
        _con = obtener_conexion_directa()
        try:
            if not _con:
                raise RuntimeError("No fue posible conectar con PostgreSQL")
            with _con.cursor() as _cur:
                _cur.execute("SELECT id_grado FROM cursos WHERE id_curso=%s;", (id_curso_sel,))
                _row = _cur.fetchone()
                st.session_state[cache_grado_key] = _row[0] if _row else None
        except Exception:
            st.session_state[cache_grado_key] = None
        finally:
            if _con:
                _con.close()

    id_grado_real = st.session_state[cache_grado_key]
    plan_grado = web_obtener_plan_estudio(id_grado_real) if id_grado_real else []

    if not plan_grado:
        st.warning("Este curso no tiene asignaturas en el Plan de Estudio. "
                   "Agréguelas en Académico → Plan de Estudio.")
        st.stop()

    with fd:
        idx_asig_n = st.selectbox(
            "Asignatura",
            options=range(len(plan_grado)),
            format_func=lambda i: plan_grado[i]["nombre_asignatura"],
            key="notas_asig"
        )
    asig_sel    = plan_grado[idx_asig_n]
    id_asig_n   = asig_sel["id_asignatura"]

    st.write("---")

    # ── Indicadores del período (solo vista informativa) ───────────────────────
    inds_boletin = web_obtener_indicadores(ano_notas, id_grado_real, id_asig_n, num_periodo_n)
    if inds_boletin:
        with st.expander(
            f"📝 Aprendizajes del {periodo_sel['nombre']} — {asig_sel['nombre_asignatura']}",
            expanded=False
        ):
            TIPO_COLOR_N = {"Cognitivo":"🔵","Procedimental":"🟢","Actitudinal":"🟡"}
            for ind in inds_boletin:
                icon = TIPO_COLOR_N.get(ind["tipo"], "•")
                st.markdown(f"{icon} **{ind['tipo']}:** {ind['descripcion']}")

    # ── Cargar estudiantes y notas existentes ─────────────────────────────────
    cache_est = f"est_curso_{id_curso_sel}_{ano_notas}"
    if cache_est not in st.session_state:
        st.session_state[cache_est] = web_obtener_estudiantes_por_curso(id_curso_sel, ano_notas)
    estudiantes_n = st.session_state[cache_est]

    if not estudiantes_n:
        st.warning("No hay estudiantes matriculados activos en este curso para el año seleccionado.")
        st.stop()

    cache_cal = f"cal_{id_curso_sel}_{ano_notas}_{num_periodo_n}_{id_asig_n}"
    if cache_cal not in st.session_state:
        st.session_state[cache_cal] = web_obtener_calificaciones(
            id_curso_sel, ano_notas, num_periodo_n, id_asig_n
        )
    notas_actuales = st.session_state[cache_cal]

    # Cargar escala
    if "escala_cache" not in st.session_state:
        st.session_state.escala_cache = web_obtener_escala()
    escala_n = st.session_state.escala_cache

    DESEMPENO_COLORES = {
        "BAJO":     ("#fee2e2", "#991b1b"),
        "BASICO":   ("#fef3c7", "#92400e"),
        "ALTO":     ("#d1fae5", "#065f46"),
        "SUPERIOR": ("#dbeafe", "#1e40af"),
        "":         ("#f3f4f6", "#6b7280"),
    }

    st.markdown(
        f"### 📋 {asig_sel['nombre_asignatura']} — {periodo_sel['nombre']} "
        f"— {curso_sel['grado']} Gr. {curso_sel['grupo']}"
    )
    st.caption(f"{len(estudiantes_n)} estudiante(s) matriculado(s)")

    # ── Formulario de notas ───────────────────────────────────────────────────
    with st.form("form_notas_bulk"):
        # Cabecera
        hc = st.columns([4, 1.8, 2.5])
        hc[0].markdown("**Estudiante**")
        hc[1].markdown("**Nota (0–5)**")
        hc[2].markdown("**Desempeño**")

        registros_form = []
        for est in estudiantes_n:
            id_mat = est["id_matricula"]
            nota_prev = notas_actuales.get(id_mat, {}).get("valor")

            ec = st.columns([4, 1.8, 2.5])
            with ec[0]:
                st.write(est["nombre_completo"].strip())
            with ec[1]:
                val = st.number_input(
                    "Nota", min_value=0.0, max_value=5.0, step=0.1,
                    value=float(nota_prev) if nota_prev is not None else 0.0,
                    format="%.1f",
                    key=f"nota_{id_mat}",
                    label_visibility="collapsed"
                )
            with ec[2]:
                id_nv, nombre_nv = web_nivel_para_valor(val, escala_n)
                bg, fg = DESEMPENO_COLORES.get(id_nv, DESEMPENO_COLORES[""])
                st.markdown(
                    f"<div style='background:{bg};color:{fg};border-radius:10px;"
                    f"padding:4px 10px;font-weight:700;font-size:12px;"
                    f"text-align:center;margin-top:4px'>{nombre_nv}</div>",
                    unsafe_allow_html=True
                )

            registros_form.append({
                "id_matricula":   id_mat,
                "id_asignatura":  id_asig_n,
                "numero_periodo": num_periodo_n,
                "ano_lectivo":    ano_notas,
                "valor":          val,
                "observacion":    notas_actuales.get(id_mat, {}).get("observacion", ""),
            })

        btn_guardar_notas = st.form_submit_button(
            "💾 Guardar todas las notas", use_container_width=True, type="primary"
        )

    if btn_guardar_notas:
        with st.spinner("Guardando calificaciones…"):
            ok_n, msg_n, cnt_n = web_guardar_calificaciones_bulk(registros_form)
        if ok_n:
            _flash_set("success", f"✅ {msg_n}")
            if cache_cal in st.session_state:
                del st.session_state[cache_cal]
            st.rerun()
        else:
            _flash_set("error", f"❌ {msg_n}")

    if st.button("🔄 Actualizar", key="notas_refresh"):
        for k in [cache_cal, cache_est]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    # ── Sección: Inasistencias y observaciones (datos para el boletín) ─────────
    st.write("---")
    with st.expander("📋 Inasistencias y observaciones del período (datos para el boletín)",
                     expanded=False):
        st.caption("Estos datos aparecerán en el boletín impreso de cada estudiante.")
        with st.form("form_boletin_datos"):
            bd_registros = []
            for est in estudiantes_n:
                id_mat = est["id_matricula"]
                bd = web_obtener_boletin_datos(id_mat, num_periodo_n)
                col_n, col_i, col_o = st.columns([4, 1.5, 5])
                col_n.write(est["nombre_completo"].strip())
                with col_i:
                    inas = st.number_input("Inasistencias", min_value=0, max_value=200,
                                           value=int(bd["inasistencias"]),
                                           key=f"inas_{id_mat}_{num_periodo_n}",
                                           label_visibility="collapsed")
                with col_o:
                    obs = st.text_input("Observaciones", value=bd["observaciones"],
                                        placeholder="Observaciones del período…",
                                        key=f"obs_{id_mat}_{num_periodo_n}",
                                        label_visibility="collapsed")
                bd_registros.append((id_mat, inas, obs))
            btn_bd = st.form_submit_button("💾 Guardar inasistencias y observaciones",
                                            use_container_width=True)
        if btn_bd:
            errores = []
            for id_mat, inas, obs in bd_registros:
                ok_bd, _ = web_guardar_boletin_datos(id_mat, num_periodo_n, inas, obs)
                if not ok_bd:
                    errores.append(id_mat)
            if errores:
                st.error(f"❌ Error guardando {len(errores)} registro(s).")
            else:
                st.success(f"✅ Inasistencias y observaciones guardadas para {len(bd_registros)} estudiante(s).")


# ==========================================
# 📄 BOLETINES
# ==========================================
elif opcion == "📄 Boletines":
    from datetime import date as _dt4
    import sys as _sys
    _sys.path.insert(0, "backend")
    from boletin_generator import generar_boletin_pdf

    st.title("📄 Generación de Boletines")
    st.write("Seleccione el curso y período, revise los datos y genere el PDF.")

    # ── Filtros ───────────────────────────────────────────────────────────────
    fa_b, fb_b, fc_b = st.columns([1.5, 2.5, 2])

    with fa_b:
        ano_bol = st.number_input("Año lectivo", min_value=2020, max_value=2050,
                                   value=_dt4.today().year, step=1, key="bol_ano")
    if "cursos_completo_cache" not in st.session_state:
        st.session_state.cursos_completo_cache = web_obtener_cursos_completo()
    cursos_bol = [c for c in st.session_state.cursos_completo_cache if c["ano"] == ano_bol]
    if not cursos_bol:
        st.warning(f"No hay cursos registrados para {ano_bol}.")
        st.stop()
    with fb_b:
        idx_cur_b = st.selectbox("Curso / Grupo", options=range(len(cursos_bol)),
                                  format_func=lambda i: f"{cursos_bol[i]['grado']} — Grupo {cursos_bol[i]['grupo']}",
                                  key="bol_curso")
    curso_b    = cursos_bol[idx_cur_b]
    id_curso_b = curso_b["id_curso"]

    periodos_b = web_obtener_periodos(ano_bol)
    if not periodos_b:
        st.warning(f"No hay períodos configurados para {ano_bol}.")
        st.stop()
    with fc_b:
        idx_per_b = st.selectbox("Período", options=range(len(periodos_b)),
                                  format_func=lambda i: periodos_b[i]["nombre"],
                                  key="bol_per")
    periodo_b     = periodos_b[idx_per_b]
    num_periodo_b = periodo_b["numero"]
    periodo_nombre_b = f"{periodo_b['nombre']} {ano_bol}"

    st.write("---")

    # ── Lista de estudiantes con datos de boletín ─────────────────────────────
    matriculas_b = web_obtener_matriculas_activas_curso(id_curso_b, ano_bol)
    if not matriculas_b:
        st.warning("No hay estudiantes matriculados activos en este curso.")
        st.stop()

    # Contexto de selección actual (para aislar cache y widget keys)
    _ctx_b = f"{ano_bol}__{id_curso_b}__{num_periodo_b}"

    # Limpiar cache de PDFs si el contexto cambió
    if st.session_state.get("bol_ctx_prev") != _ctx_b:
        for k in list(st.session_state.keys()):
            if k.startswith("pdf_bol_"):
                del st.session_state[k]
        st.session_state["bol_ctx_prev"] = _ctx_b

    st.markdown(f"### 📋 Estudiantes — {curso_b['grado']} Gr. {curso_b['grupo']}")
    st.caption(f"{len(matriculas_b)} estudiante(s) · {periodo_b['nombre']}")

    # Escala para mostrar promedios
    if "escala_cache" not in st.session_state:
        st.session_state.escala_cache = web_obtener_escala()
    escala_b = st.session_state.escala_cache

    # ── Cargar promedios y datos de boletín en una sola consulta cada uno ─────
    ids_mat_b    = [r[0] for r in matriculas_b]
    promedios_b  = web_obtener_promedios_periodo(ids_mat_b, num_periodo_b)
    bd_previos_b = web_obtener_boletin_datos_bulk(ids_mat_b, num_periodo_b)

    # ── Tabla resumen + edición de inasistencias/observaciones ───────────────
    with st.form(f"form_bd_boletin_{_ctx_b}"):
        h0, h1, h2, h3, h4 = st.columns([4, 1.5, 2, 2, 4])
        for lbl, col in zip(["Estudiante","Promedio","Nivel","Inasistencias","Observaciones"],
                             [h0, h1, h2, h3, h4]):
            col.markdown(f"**{lbl}**")

        bd_rows = []
        for id_mat, nom in matriculas_b:
            prom_b  = promedios_b.get(id_mat)
            _, niv_nom = web_nivel_para_valor(prom_b, escala_b) if prom_b is not None \
                         else ("", "Sin notas")
            bd_prev = bd_previos_b.get(id_mat, {"inasistencias": 0, "observaciones": ""})

            r0, r1, r2, r3, r4 = st.columns([4, 1.5, 2, 2, 4])
            r0.write(nom.strip())
            r1.write(f"{prom_b:.2f}".replace(".", ",") if prom_b is not None else "—")
            r2.write(niv_nom)
            with r3:
                inas_b = st.number_input(
                    "Inas", min_value=0, max_value=200,
                    value=int(bd_prev["inasistencias"]),
                    key=f"bd_i_{_ctx_b}_{id_mat}",
                    label_visibility="collapsed"
                )
            with r4:
                obs_b = st.text_input(
                    "Obs", value=bd_prev["observaciones"],
                    placeholder="Observaciones…",
                    key=f"bd_o_{_ctx_b}_{id_mat}",
                    label_visibility="collapsed"
                )
            bd_rows.append((id_mat, nom, inas_b, obs_b, prom_b))

        btn_save_bd = st.form_submit_button(
            "💾 Guardar inasistencias y observaciones", use_container_width=True
        )

    if btn_save_bd:
        errs = 0
        for id_mat, _, inas_b, obs_b, _ in bd_rows:
            ok_s, _ = web_guardar_boletin_datos(id_mat, num_periodo_b, inas_b, obs_b)
            if not ok_s:
                errs += 1
        if errs:
            st.error(f"❌ Error en {errs} registro(s).")
        else:
            st.success(f"✅ Datos guardados para {len(bd_rows)} estudiante(s).")

    st.write("---")

    # ── Generación de PDFs ────────────────────────────────────────────────────
    st.markdown("### 🖨️ Generar boletines PDF")
    inst_b = st.session_state.get("inst_data") or {}

    _key_pdf_curso = f"pdf_bol_curso_{_ctx_b}"
    col_gen1, col_gen2 = st.columns([1, 1])
    with col_gen1:
        if st.button("📥 PDF Curso Completo", use_container_width=True, type="primary"):
            with st.spinner(f"Generando {len(matriculas_b)} boletín(es)…"):
                datos_todos = [
                    web_datos_para_boletin(id_mat, num_periodo_b, ano_bol)
                    for id_mat, _ in matriculas_b
                ]
                pdf_buf = generar_boletin_pdf(datos_todos, periodo_nombre_b, inst_b, escala_b)
                st.session_state[_key_pdf_curso] = {
                    "bytes": pdf_buf.getvalue(),
                    "nombre": (
                        f"Boletin_{curso_b['grado'].replace(' ','_')}_Gr{curso_b['grupo']}"
                        f"_P{num_periodo_b}_{ano_bol}.pdf"
                    ),
                }
            _flash_set("success", "✅ PDF generado. Use el botón de descarga.")
            st.rerun()

    if _key_pdf_curso in st.session_state:
        with col_gen2:
            _pdf_c = st.session_state[_key_pdf_curso]
            st.download_button(
                label="⬇️ Descargar PDF del curso",
                data=_pdf_c["bytes"],
                file_name=_pdf_c["nombre"],
                mime="application/pdf",
                use_container_width=True,
            )

    st.write("---")
    st.markdown("#### 📑 Boletines individuales")
    for id_mat, nom in matriculas_b:
        _key_ind = f"pdf_bol_ind_{_ctx_b}_{id_mat}"
        col_n, col_btn, col_dl = st.columns([5, 1.5, 1.5])
        col_n.write(nom.strip())
        with col_btn:
            if st.button("📥 Generar", key=f"gen_ind_{_ctx_b}_{id_mat}",
                         use_container_width=True):
                with st.spinner("Generando…"):
                    d_ind   = web_datos_para_boletin(id_mat, num_periodo_b, ano_bol)
                    pdf_ind = generar_boletin_pdf([d_ind], periodo_nombre_b, inst_b, escala_b)
                    nombre_pdf = nom.strip().replace(" ", "_")[:30]
                    st.session_state[_key_ind] = {
                        "bytes":  pdf_ind.getvalue(),
                        "nombre": f"Boletin_{nombre_pdf}_P{num_periodo_b}.pdf",
                    }
                st.rerun()
        with col_dl:
            if _key_ind in st.session_state:
                _pdf_i = st.session_state[_key_ind]
                st.download_button(
                    label="⬇️ Descargar",
                    data=_pdf_i["bytes"],
                    file_name=_pdf_i["nombre"],
                    mime="application/pdf",
                    key=f"dl_ind_{_ctx_b}_{id_mat}",
                    use_container_width=True,
                )
