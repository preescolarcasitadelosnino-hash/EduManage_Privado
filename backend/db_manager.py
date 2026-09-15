
import psycopg2
from psycopg2 import errors, pool as psycopg2_pool
import streamlit as st
import bcrypt

# ==========================================
# 🔌 CONEXIÓN A POSTGRESQL
# ==========================================


class _ConexionDelPool:
    """Adaptador compatible con ``psycopg2 connection``.

    El código existente llama a ``close()`` en muchos módulos. En vez de
    cerrar físicamente la conexión, aquí ``close()`` la devuelve al pool.
    Así se conserva la compatibilidad sin dejar conexiones prestadas.
    """

    def __init__(self, pool_conexiones, conexion):
        self._pool_conexiones = pool_conexiones
        self._conexion = conexion
        self._devuelta = False

    def __getattr__(self, nombre):
        return getattr(self._conexion, nombre)

    def close(self):
        """Devuelve la conexión al pool de forma idempotente y segura."""
        if self._devuelta:
            return

        self._devuelta = True
        cerrar_fisicamente = False

        try:
            if self._conexion.closed:
                cerrar_fisicamente = True
            else:
                try:
                    # Evita que una transacción abortada contamine al
                    # siguiente usuario de esta conexión.
                    self._conexion.rollback()
                except Exception:
                    cerrar_fisicamente = True

                if self._conexion.closed:
                    cerrar_fisicamente = True

            self._pool_conexiones.putconn(
                self._conexion,
                close=cerrar_fisicamente,
            )
        except Exception:
            # Si el pool ya no acepta la conexión, no la dejamos viva ni
            # retenida. El siguiente uso obtendrá una conexión nueva.
            try:
                self._conexion.close()
            except Exception:
                pass


@st.cache_resource(show_spinner=False)
def obtener_pool_conexiones():
    """Crea un pool por proceso de Streamlit y lo reutiliza entre reruns."""
    minconn = int(st.secrets.get("DB_POOL_MINCONN", 1))
    maxconn = int(st.secrets.get("DB_POOL_MAXCONN", 5))
    if minconn < 1 or maxconn < minconn:
        raise ValueError("DB_POOL_MINCONN/DB_POOL_MAXCONN tienen valores inválidos")

    return psycopg2_pool.ThreadedConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        host=st.secrets["DB_HOST"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets.get("DB_PORT", "5432"),
        sslmode=st.secrets.get("DB_SSLMODE", "require"),
    )


def obtener_conexion_directa():
    """Obtiene una conexión reutilizable y compatible con el código actual."""
    try:
        pool_conexiones = obtener_pool_conexiones()
        conexion = pool_conexiones.getconn()

        # Un servidor remoto puede haber cerrado una conexión inactiva. No
        # devolvemos ese socket al código de aplicación.
        if conexion.closed:
            pool_conexiones.putconn(conexion, close=True)
            conexion = pool_conexiones.getconn()

        return _ConexionDelPool(pool_conexiones, conexion)

    except Exception as error:
        st.error(f"❌ Error de conexión a PostgreSQL: {error}")
        return None



# ==========================================
# 🔍 FUNCIONES DE CONSULTA
# ==========================================


def web_obtener_cursos():
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cursor:
            cursor.execute("""
                SELECT id_curso FROM cursos ORDER BY id_curso;
            """)
            return [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar cursos: {e}")
        return []
    finally:
        con.close()



# ==========================================
# ✍️ FUNCIONES DE REGISTRO
# ==========================================



# ==========================================
# 📚 GRUPOS / CURSOS
# ==========================================

def web_obtener_grados_con_detalle():
    """Retorna lista de dicts con todos los datos de grados ordenados por su campo 'orden'."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT id_grado, nombre_grado, nivel, orden 
                FROM grados 
                ORDER BY orden ASC;
            """)
            cols = ["id_grado", "nombre_grado", "nivel", "orden"]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar grados con detalle: {e}")
        return []
    finally:
        con.close()

def web_obtener_grados():
    """Retorna lista de (id_grado, nombre_grado) ordenada por orden, nombre."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_grado, nombre_grado FROM grados "
                "ORDER BY CASE nivel "
                "  WHEN 'PREESCOLAR' THEN 1 WHEN 'PRIMARIA' THEN 2 "
                "  WHEN 'SECUNDARIA' THEN 3 WHEN 'MEDIA' THEN 4 ELSE 5 END, "
                "orden, nombre_grado;"
            )
            return cur.fetchall()
    except Exception:
        return []
    finally:
        con.close()


def web_obtener_sedes():
    """Retorna lista de (id_sede, nombre_sede) ordenada. Uso interno y selectboxes."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id_sede, nombre_sede FROM sedes ORDER BY nombre_sede;")
            return cur.fetchall()
    except Exception:
        return []
    finally:
        con.close()


def web_obtener_sedes_completo():
    """Retorna lista de dicts con todos los campos de sedes."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_sede, nombre_sede, direccion, telefono_sede, id_institucion "
                "FROM sedes ORDER BY nombre_sede;"
            )
            cols = ["id_sede", "nombre_sede", "direccion", "telefono_sede", "id_institucion"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def web_registrar_sede(nombre, direccion="", telefono=""):
    """Crea una nueva sede. Retorna (bool, mensaje, id_generado|None)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos.", None
    try:
        with con.cursor() as cur:
            cur.execute("SELECT nextval('seq_id_sede');")
            id_sede = f"SED-{cur.fetchone()[0]:03d}"
            cur.execute(
                "INSERT INTO sedes (id_sede, id_institucion, nombre_sede, direccion, telefono_sede) "
                "VALUES (%s, 'INST-DICA', %s, %s, %s);",
                (id_sede, nombre.strip(), direccion.strip() or None, telefono.strip() or None)
            )
        con.commit()
        return True, f"Sede '{nombre}' registrada con código {id_sede}.", id_sede
    except errors.UniqueViolation:
        con.rollback()
        return False, "Ya existe una sede con ese código.", None
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}", None
    finally:
        con.close()


def web_actualizar_sede(id_sede, nombre, direccion="", telefono=""):
    """Actualiza los datos de una sede existente. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE sedes SET nombre_sede=%s, direccion=%s, telefono_sede=%s "
                "WHERE id_sede=%s;",
                (nombre.strip(), direccion.strip() or None, telefono.strip() or None, id_sede)
            )
            if cur.rowcount == 0:
                return False, f"No se encontró la sede '{id_sede}'."
        con.commit()
        return True, f"Sede '{nombre}' actualizada correctamente."
    except Exception as e:
        con.rollback()
        return False, f"Error al actualizar: {e}"
    finally:
        con.close()


def web_eliminar_sede(id_sede):
    """Elimina una sede. Falla si tiene cursos asignados. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            # Verificar cursos dependientes
            cur.execute("SELECT COUNT(*) FROM cursos WHERE id_sede = %s;", (id_sede,))
            n_cursos = cur.fetchone()[0]
            if n_cursos > 0:
                return (
                    False,
                    f"No se puede eliminar: la sede tiene {n_cursos} grupo(s) asignado(s). "
                    "Reasigne o elimine los grupos primero."
                )
            cur.execute("DELETE FROM sedes WHERE id_sede = %s;", (id_sede,))
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, f"Sede '{id_sede}' eliminada correctamente."
        return False, f"No se encontró la sede '{id_sede}'."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


def web_obtener_jornadas():
    """Retorna lista de (id_jornada, nombre_jornada) ordenada."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id_jornada, nombre_jornada FROM jornadas ORDER BY id_jornada;")
            return cur.fetchall()
    except Exception:
        return []
    finally:
        con.close()


from psycopg2 import errors

def web_obtener_cursos_completo():
    """Retorna lista de dicts con todos los cursos enriquecidos (nombres de grado, sede y jornada)."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT c.id_curso, g.nombre_grado, c.grupo, 
                       s.nombre_sede, j.nombre_jornada
                FROM cursos c
                JOIN grados   g ON g.id_grado   = c.id_grado
                JOIN sedes    s ON s.id_sede    = c.id_sede
                JOIN jornadas j ON j.id_jornada = c.id_jornada
                ORDER BY g.id_grado, c.grupo;
            """)
            cols = ["id_curso", "grado", "grupo", "sede", "jornada"]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar cursos: {e}")
        return []
    finally:
        con.close()


def web_registrar_curso(id_curso, id_grado, grupo, id_sede, id_jornada):
    """Inserta un nuevo curso/grupo. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO cursos (id_curso, id_grado, grupo, id_sede, id_jornada)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_curso, id_grado, grupo, id_sede, id_jornada))
        con.commit()
        return True, f"Grupo '{id_curso}' creado exitosamente."
    except errors.UniqueViolation:
        con.rollback()
        return False, f"Ya existe un grupo con el codigo '{id_curso}'."
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}"
    finally:
        con.close()

def formatear_nombre_grupo(nombre_grado, numero_grupo, formato="numerico"):
    """
    Retorna el nombre del grupo formateado dinámicamente.
    - formato="numerico" -> Ej: "6-01" (extrae el número del grado si lo tiene)
    - formato="textual"  -> Ej: "Sexto 01"
    """
    import re
    # Intentar extraer un dígito del nombre del grado para el formato numérico
    match = re.search(r'\d+', nombre_grado)
    num_grado = match.group() if match else nombre_grado
    
    if formato == "numerico":
        return f"{num_grado}-{numero_grupo}"
    else:  # textual
        return f"{nombre_grado} {numero_grupo}"


def web_eliminar_curso(id_curso):
    """Elimina un curso/grupo por su ID. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("DELETE FROM cursos WHERE id_curso = %s;", (id_curso,))
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, f"Grupo '{id_curso}' eliminado correctamente."
        return False, f"No se encontro ningun grupo con codigo '{id_curso}'."
    except errors.ForeignKeyViolation:
        con.rollback()
        return False, (
            f"No se puede eliminar el grupo '{id_curso}' porque tiene matrículas, "
            "direcciones de grupo u otros registros asociados."
        )
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


def web_actualizar_curso(id_curso, id_grado, grupo, id_sede, id_jornada):
    """Actualiza los datos de un curso existente. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE cursos
                SET id_grado = %s, grupo = %s,
                    id_sede = %s, id_jornada = %s
                WHERE id_curso = %s;
            """, (id_grado, grupo, id_sede, id_jornada, id_curso))
            actualizados = cur.rowcount
        con.commit()
        if actualizados:
            return True, f"Grupo '{id_curso}' actualizado correctamente."
        return False, f"No se encontro ningun grupo con codigo '{id_curso}'."
    except errors.UniqueViolation:
        con.rollback()
        return False, "Ya existe otro grupo con los mismos datos."
    except Exception as e:
        con.rollback()
        return False, f"Error al actualizar: {e}"
    finally:
        con.close()


# ==========================================
# 👨‍🏫 DIRECCIONES DE GRUPO
# ==========================================

def web_generar_codigo_direccion_grupo():
    """Devuelve el siguiente codigo disponible para una direccion de grupo (ej: DG-1).
    Usa la secuencia PostgreSQL seq_id_direccion_grupo para garantizar atomicidad.
    Retorna None si no hay conexion.
    """
    con = obtener_conexion_directa()
    if not con:
        return None
    try:
        with con.cursor() as cur:
            cur.execute("SELECT nextval('seq_id_direccion_grupo');")
            siguiente = cur.fetchone()[0]
            return f"DG-{siguiente}"
    except Exception as e:
        st.error(f"Error al generar codigo de direccion de grupo: {e}")
        return None
    finally:
        con.close()


def web_registrar_direccion_grupo(id_dg, id_curso, id_personal, ano_lectivo):
    """Registra un director de grupo para un curso y año lectivo.
    Retorna (bool, mensaje).
    Restricciones garantizadas en BD:
      - Un curso solo puede tener un director por año lectivo.
      - Un docente solo puede dirigir un grupo por año lectivo.
    """
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cursor:
            cursor.execute("""
                INSERT INTO direcciones_grupo
                    (id_direccion_grupo, id_curso, id_personal, ano_lectivo)
                VALUES (%s, %s, %s, %s)
            """, (id_dg, id_curso, id_personal, ano_lectivo))
            con.commit()
            return True, f"Direccion de grupo '{id_dg}' registrada exitosamente."
    except errors.UniqueViolation as e:
        con.rollback()
        constraint = getattr(e.diag, "constraint_name", "") or ""
        if constraint == "uq_curso_ano":
            return False, "Este curso ya tiene un director asignado para ese año lectivo."
        if constraint == "uq_personal_ano":
            return False, "Este docente ya es director de otro grupo en ese año lectivo."
        return False, "Ya existe una direccion de grupo con esos datos."
    except errors.ForeignKeyViolation as e:
        con.rollback()
        constraint = getattr(e.diag, "constraint_name", "") or ""
        if constraint == "direcciones_grupo_id_curso_fkey":
            return False, f"El curso '{id_curso}' no existe en el sistema."
        if constraint == "direcciones_grupo_id_personal_fkey":
            return False, f"El docente '{id_personal}' no existe en el sistema."
        return False, "Referencia invalida: verifique el curso y el docente."
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}"
    finally:
        con.close()


def web_consultar_direcciones_grupo(ano_lectivo=None):
    """Devuelve lista de dicts con todas las direcciones de grupo.
    Si se pasa ano_lectivo (int), filtra por ese año.
    Cada dict incluye datos del curso, del grado y del docente.
    """
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            sql = """
                SELECT
                    dg.id_direccion_grupo,
                    dg.id_curso,
                    c.id_grado,
                    c.grupo,
                    c.id_sede,
                    c.id_jornada,
                    dg.id_personal,
                    p.nombres || ' ' || p.apellidos  AS nombre_director,
                    p.rol,
                    dg.ano_lectivo
                FROM direcciones_grupo dg
                JOIN cursos   c ON c.id_curso    = dg.id_curso
                JOIN personal p ON p.id_personal = dg.id_personal
            """
            if ano_lectivo is not None:
                sql += " WHERE dg.ano_lectivo = %s"
                sql += " ORDER BY dg.ano_lectivo DESC, dg.id_curso;"
                cur.execute(sql, (ano_lectivo,))
            else:
                sql += " ORDER BY dg.ano_lectivo DESC, dg.id_curso;"
                cur.execute(sql)
            cols = [
                "id_direccion_grupo", "id_curso", "id_grado", "grupo",
                "id_sede", "id_jornada", "id_personal", "nombre_director",
                "rol", "ano_lectivo"
            ]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        st.error(f"Error al consultar direcciones de grupo: {e}")
        return []
    finally:
        con.close()


def web_eliminar_direccion_grupo(id_dg):
    """Elimina una asignacion de director de grupo por su ID.
    Retorna (bool, mensaje).
    """
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM direcciones_grupo WHERE id_direccion_grupo = %s;",
                (id_dg,)
            )
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, f"Asignacion '{id_dg}' eliminada correctamente."
        return False, f"No se encontro ninguna asignacion con ID '{id_dg}'."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


# ==========================================
# 📖 ASIGNATURAS
# ==========================================

def web_registrar_asignatura(nombre, area_conocimiento, descripcion="", nivel="TODOS"):
    """Crea una nueva asignatura en el catalogo. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("SELECT nextval('seq_id_asignatura');")
            id_asg = f"ASG-{cur.fetchone()[0]:03d}"
            cur.execute(
                "INSERT INTO asignaturas (id_asignatura, nombre, area_conocimiento, descripcion, nivel) "
                "VALUES (%s, %s, %s, %s, %s);",
                (id_asg, nombre.strip(), area_conocimiento.strip(),
                 descripcion.strip() or None, nivel)
            )
        con.commit()
        return True, f"Asignatura '{nombre}' registrada con codigo {id_asg}."
    except errors.UniqueViolation:
        con.rollback()
        return False, "Ya existe una asignatura con ese codigo."
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}"
    finally:
        con.close()


def web_actualizar_asignatura(id_asignatura, nombre, area_conocimiento, descripcion, nivel):
    """Actualiza nombre, area, descripcion y nivel de una asignatura. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE asignaturas
                SET nombre = %s, area_conocimiento = %s,
                    descripcion = %s, nivel = %s
                WHERE id_asignatura = %s;
            """, (nombre.strip(), area_conocimiento.strip(),
                  descripcion.strip() or None, nivel, id_asignatura))
            actualizados = cur.rowcount
        con.commit()
        if actualizados:
            return True, f"Asignatura '{nombre}' actualizada."
        return False, f"No se encontro la asignatura '{id_asignatura}'."
    except Exception as e:
        con.rollback()
        return False, f"Error al actualizar: {e}"
    finally:
        con.close()


def web_obtener_asignaturas():
    """Retorna lista de dicts con todas las asignaturas del catalogo."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_asignatura, nombre, area_conocimiento, descripcion, nivel "
                "FROM asignaturas ORDER BY nivel, area_conocimiento, nombre;"
            )
            cols = ["id_asignatura", "nombre", "area_conocimiento", "descripcion", "nivel"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def web_eliminar_asignatura(id_asignatura):
    """Elimina una asignatura del catalogo. Falla si tiene dependencias.
    Retorna (bool, mensaje).
    """
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM asignaturas WHERE id_asignatura = %s;",
                (id_asignatura,)
            )
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, f"Asignatura '{id_asignatura}' eliminada."
        return False, f"No se encontro la asignatura '{id_asignatura}'."
    except errors.ForeignKeyViolation:
        con.rollback()
        return False, "No se puede eliminar: la asignatura esta en uso en un Plan de Estudio o Asignacion Docente."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


# ==========================================
# 📋 PLAN DE ESTUDIO
# ==========================================

def web_registrar_plan_estudio(id_grado, id_asignatura, horas_semana):
    """Agrega una asignatura al plan de estudio de un grado. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute("SELECT nextval('seq_id_plan_estudio');")
            id_plan = f"PE-{cur.fetchone()[0]:03d}"
            cur.execute(
                "INSERT INTO plan_estudio (id_plan, id_grado, id_asignatura, horas_semana) "
                "VALUES (%s, %s, %s, %s);",
                (id_plan, id_grado, id_asignatura, int(horas_semana))
            )
        con.commit()
        return True, f"Asignatura agregada al plan de estudio de {id_grado}."
    except errors.UniqueViolation:
        con.rollback()
        return False, "Esta asignatura ya esta en el plan de estudio de ese grado."
    except errors.ForeignKeyViolation as e:
        con.rollback()
        c = getattr(e.diag, "constraint_name", "") or ""
        if "id_grado" in c:
            return False, f"El grado '{id_grado}' no existe."
        return False, f"La asignatura no existe en el catalogo."
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}"
    finally:
        con.close()


def web_obtener_plan_estudio(id_grado=None):
    """Retorna el plan de estudio completo o filtrado por grado.
    Cada dict incluye nombre de grado y nombre de asignatura.
    """
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            sql = (
                "SELECT pe.id_plan, pe.id_grado, g.nombre_grado, "
                "       pe.id_asignatura, a.nombre, a.area_conocimiento, pe.horas_semana "
                "FROM plan_estudio pe "
                "JOIN grados g ON g.id_grado = pe.id_grado "
                "JOIN asignaturas a ON a.id_asignatura = pe.id_asignatura "
            )
            if id_grado is not None:
                sql += "WHERE pe.id_grado = %s "
                sql += "ORDER BY a.area_conocimiento, a.nombre;"
                cur.execute(sql, (id_grado,))
            else:
                sql += "ORDER BY g.id_grado, a.area_conocimiento, a.nombre;"
                cur.execute(sql)
            cols = ["id_plan", "id_grado", "nombre_grado",
                    "id_asignatura", "nombre_asignatura", "area", "horas_semana"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar plan de estudio: {e}")
        return []
    finally:
        con.close()


def web_actualizar_horas_plan(id_plan, horas_semana):
    """Actualiza las horas semanales de una entrada del plan de estudio. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE plan_estudio SET horas_semana = %s WHERE id_plan = %s;",
                (int(horas_semana), id_plan)
            )
            actualizados = cur.rowcount
        con.commit()
        if actualizados:
            return True, f"Horas actualizadas a {horas_semana} h/sem."
        return False, f"No se encontro el registro '{id_plan}'."
    except Exception as e:
        con.rollback()
        return False, f"Error al actualizar: {e}"
    finally:
        con.close()


def web_eliminar_plan_estudio(id_plan):
    """Elimina una entrada del plan de estudio.
    Bloquea si hay asignaciones docentes activas para la asignatura en cursos del mismo grado.
    Retorna (bool, mensaje).
    """
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            # Obtener grado e id_asignatura de la entrada a eliminar
            cur.execute(
                "SELECT id_grado, id_asignatura FROM plan_estudio WHERE id_plan = %s;",
                (id_plan,)
            )
            fila = cur.fetchone()
            if not fila:
                return False, f"No se encontro el registro '{id_plan}'."
            id_grado_plan, id_asg_plan = fila

            # Verificar asignaciones docentes activas para esa asignatura en cursos del grado
            cur.execute(
                "SELECT COUNT(*) FROM asignacion_docente ad "
                "JOIN cursos c ON c.id_curso = ad.id_curso "
                "WHERE c.id_grado = %s AND ad.id_asignatura = %s;",
                (id_grado_plan, id_asg_plan)
            )
            activas = cur.fetchone()[0]
            if activas > 0:
                return (
                    False,
                    f"No se puede retirar: hay {activas} asignacion(es) docente(s) activa(s) "
                    "para esta asignatura en cursos de este grado. "
                    "Elimine primero las asignaciones docentes correspondientes."
                )

            cur.execute("DELETE FROM plan_estudio WHERE id_plan = %s;", (id_plan,))
        con.commit()
        return True, "Asignatura retirada del plan de estudio."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


def web_obtener_asignaturas_sin_asignar(id_grado):
    """Retorna asignaturas que NO estan en el plan del grado dado,
    filtradas por el nivel del grado (o nivel='TODOS').
    Util para poblar el selectbox de 'Agregar asignatura'.
    """
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT a.id_asignatura, a.nombre, a.area_conocimiento, a.nivel
                FROM asignaturas a
                WHERE a.id_asignatura NOT IN (
                    SELECT id_asignatura FROM plan_estudio WHERE id_grado = %s
                )
                AND (
                    a.nivel = 'TODOS'
                    OR a.nivel = (SELECT nivel FROM grados WHERE id_grado = %s)
                )
                ORDER BY a.area_conocimiento, a.nombre;
                """,
                (id_grado, id_grado)
            )
            return cur.fetchall()  # [(id, nombre, area, nivel), ...]
    except Exception:
        return []
    finally:
        con.close()


# ==========================================
# 👩‍🏫 ASIGNACIÓN DOCENTE
# ==========================================

def web_registrar_asignacion_docente(id_curso, id_personal, id_asignatura, ano_lectivo):
    """Asigna un docente a una asignatura en un curso y año.
    Valida que la asignatura pertenezca al plan de estudio del grado del curso.
    Retorna (bool, mensaje).
    """
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            # 1. Obtener el grado del curso
            cur.execute("SELECT id_grado FROM cursos WHERE id_curso = %s;", (id_curso,))
            fila_curso = cur.fetchone()
            if not fila_curso:
                return False, f"El curso '{id_curso}' no existe en el sistema."
            id_grado = fila_curso[0]

            # 2. Verificar que la asignatura este en el plan de estudio de ese grado
            cur.execute(
                "SELECT 1 FROM plan_estudio "
                "WHERE id_grado = %s AND id_asignatura = %s;",
                (id_grado, id_asignatura)
            )
            if not cur.fetchone():
                return (
                    False,
                    f"La asignatura '{id_asignatura}' no esta en el Plan de Estudio "
                    f"del grado de este curso. Agreguela primero en Plan de Estudio."
                )

            # 3. Insertar
            cur.execute("SELECT nextval('seq_id_asignacion_docente');")
            id_ad = f"AD-{cur.fetchone()[0]:03d}"
            cur.execute(
                "INSERT INTO asignacion_docente "
                "  (id_asignacion, id_curso, id_personal, id_asignatura, ano_lectivo) "
                "VALUES (%s, %s, %s, %s, %s);",
                (id_ad, id_curso, id_personal, id_asignatura, int(ano_lectivo))
            )
        con.commit()
        return True, f"Asignacion registrada con codigo {id_ad}."
    except errors.UniqueViolation:
        con.rollback()
        return False, "Esta asignatura ya tiene un docente asignado en ese curso y año."
    except errors.ForeignKeyViolation as e:
        con.rollback()
        c = getattr(e.diag, "constraint_name", "") or ""
        if "id_personal" in c:
            return False, f"El docente '{id_personal}' no existe en el sistema."
        if "id_asignatura" in c:
            return False, f"La asignatura '{id_asignatura}' no existe en el catalogo."
        return False, "Referencia invalida. Verifique el curso, docente y asignatura."
    except Exception as e:
        con.rollback()
        return False, f"Error inesperado: {e}"
    finally:
        con.close()


def web_obtener_asignaciones_docente(id_curso=None, ano_lectivo=None):
    """Retorna lista de dicts con las asignaciones docente, con nombres completos.
    Se puede filtrar por curso, por año lectivo, o por ambos.
    """
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            sql = (
                "SELECT ad.id_asignacion, ad.id_curso, ad.id_personal, "
                "       p.nombres || ' ' || p.apellidos AS nombre_docente, p.rol, "
                "       ad.id_asignatura, a.nombre AS nombre_asignatura, "
                "       a.area_conocimiento, ad.ano_lectivo "
                "FROM asignacion_docente ad "
                "JOIN personal    p ON p.id_personal    = ad.id_personal "
                "JOIN asignaturas a ON a.id_asignatura  = ad.id_asignatura "
            )
            filtros, params = [], []
            if id_curso is not None:
                filtros.append("ad.id_curso = %s")
                params.append(id_curso)
            if ano_lectivo is not None:
                filtros.append("ad.ano_lectivo = %s")
                params.append(ano_lectivo)
            if filtros:
                sql += "WHERE " + " AND ".join(filtros) + " "
            sql += "ORDER BY a.area_conocimiento, a.nombre;"
            cur.execute(sql, params)
            cols = ["id_asignacion", "id_curso", "id_personal", "nombre_docente",
                    "rol", "id_asignatura", "nombre_asignatura", "area", "ano_lectivo"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar asignaciones: {e}")
        return []
    finally:
        con.close()


def web_eliminar_asignacion_docente(id_asignacion):
    """Elimina una asignacion docente por su ID. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible establecer conexion con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM asignacion_docente WHERE id_asignacion = %s;",
                (id_asignacion,)
            )
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, "Asignacion docente eliminada correctamente."
        return False, f"No se encontro la asignacion '{id_asignacion}'."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


# ==========================================
# 📅 PERÍODOS ACADÉMICOS
# ==========================================

def web_obtener_periodos(ano_lectivo):
    """Retorna lista de dicts con los períodos del año dado, ordenados por número."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_periodo, numero, nombre, fecha_inicio, fecha_fin, porcentaje "
                "FROM periodos_academicos WHERE ano_lectivo = %s ORDER BY numero;",
                (ano_lectivo,)
            )
            cols = ["id_periodo", "numero", "nombre", "fecha_inicio", "fecha_fin", "porcentaje"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def web_guardar_periodos(ano_lectivo, periodos):
    """Reemplaza todos los períodos del año con la lista dada.

    periodos: list[dict] con keys: numero (1-4), nombre, fecha_inicio (date|None),
              fecha_fin (date|None), porcentaje (float).
    Retorna (bool, mensaje).
    """
    # Validar lista no vacía
    if not periodos:
        return False, "Debe proporcionar al menos un período."

    # Validar que los porcentajes sumen 100
    total = sum(float(p.get("porcentaje", 0)) for p in periodos)
    if abs(total - 100.0) > 0.01:
        return False, f"Los porcentajes deben sumar 100 %. Actualmente suman {total:.2f} %."

    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            # Eliminar períodos que ya no están en la nueva configuración
            nums_nuevos = [p["numero"] for p in periodos]
            # Construir la cláusula NOT IN de forma segura para cualquier tamaño
            placeholders = ",".join(["%s"] * len(nums_nuevos))
            cur.execute(
                f"DELETE FROM periodos_academicos "
                f"WHERE ano_lectivo = %s AND numero NOT IN ({placeholders});",
                [ano_lectivo] + nums_nuevos
            )
            for p in periodos:
                cur.execute(
                    """
                    INSERT INTO periodos_academicos
                        (id_periodo, ano_lectivo, numero, nombre, fecha_inicio, fecha_fin, porcentaje)
                    VALUES (
                        COALESCE(
                            (SELECT id_periodo FROM periodos_academicos
                             WHERE ano_lectivo=%s AND numero=%s),
                            'PPER-' || LPAD(nextval('seq_id_periodo')::TEXT, 3, '0')
                        ),
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (ano_lectivo, numero) DO UPDATE SET
                        nombre        = EXCLUDED.nombre,
                        fecha_inicio  = EXCLUDED.fecha_inicio,
                        fecha_fin     = EXCLUDED.fecha_fin,
                        porcentaje    = EXCLUDED.porcentaje;
                    """,
                    (
                        ano_lectivo, p["numero"],
                        ano_lectivo, p["numero"], p["nombre"],
                        p.get("fecha_inicio"), p.get("fecha_fin"), p["porcentaje"]
                    )
                )
        con.commit()
        return True, f"{len(periodos)} período(s) guardados correctamente para {ano_lectivo}."
    except Exception as e:
        con.rollback()
        return False, f"Error al guardar períodos: {e}"
    finally:
        con.close()


# ==========================================
# 📝 INDICADORES DE DESEMPEÑO
# ==========================================

def web_obtener_indicadores(ano_lectivo, id_grado, id_asignatura, numero_periodo=None):
    """Retorna indicadores filtrados. numero_periodo=None devuelve todos los períodos."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            sql = (
                "SELECT id_indicador, numero_periodo, descripcion, tipo "
                "FROM indicadores_desempeno "
                "WHERE ano_lectivo=%s AND id_grado=%s AND id_asignatura=%s"
            )
            params = [ano_lectivo, id_grado, id_asignatura]
            if numero_periodo is not None:
                sql += " AND numero_periodo=%s"
                params.append(numero_periodo)
            sql += " ORDER BY numero_periodo, tipo, id_indicador;"
            cur.execute(sql, params)
            cols = ["id_indicador", "numero_periodo", "descripcion", "tipo"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def web_registrar_indicador(ano_lectivo, id_grado, id_asignatura,
                             numero_periodo, descripcion, tipo="Cognitivo"):
    """Crea un nuevo indicador. Retorna (bool, mensaje, id|None)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos.", None
    try:
        with con.cursor() as cur:
            cur.execute("SELECT nextval('seq_id_indicador');")
            id_ind = f"IND-{cur.fetchone()[0]:04d}"
            cur.execute(
                "INSERT INTO indicadores_desempeno "
                "(id_indicador, ano_lectivo, id_grado, id_asignatura, "
                " numero_periodo, descripcion, tipo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s);",
                (id_ind, ano_lectivo, id_grado, id_asignatura,
                 numero_periodo, descripcion.strip(), tipo)
            )
        con.commit()
        return True, f"Indicador {id_ind} registrado.", id_ind
    except Exception as e:
        con.rollback()
        return False, f"Error al registrar: {e}", None
    finally:
        con.close()


def web_actualizar_indicador(id_indicador, descripcion, tipo):
    """Actualiza descripción y tipo de un indicador. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE indicadores_desempeno "
                "SET descripcion=%s, tipo=%s WHERE id_indicador=%s;",
                (descripcion.strip(), tipo, id_indicador)
            )
            if cur.rowcount == 0:
                return False, "Indicador no encontrado."
        con.commit()
        return True, "Indicador actualizado correctamente."
    except Exception as e:
        con.rollback()
        return False, f"Error al actualizar: {e}"
    finally:
        con.close()


def web_eliminar_indicador(id_indicador):
    """Elimina un indicador. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM indicadores_desempeno WHERE id_indicador=%s;",
                (id_indicador,)
            )
            eliminados = cur.rowcount
        con.commit()
        if eliminados:
            return True, "Indicador eliminado."
        return False, "Indicador no encontrado."
    except Exception as e:
        con.rollback()
        return False, f"Error al eliminar: {e}"
    finally:
        con.close()


# ==========================================
# ⚖️ ESCALA DE VALORACIÓN
# ==========================================

def web_obtener_escala():
    """Retorna lista de dicts con los niveles de desempeño ordenados."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_nivel, nombre, valor_min, valor_max, descripcion, orden "
                "FROM escala_valoracion ORDER BY orden;"
            )
            cols = ["id_nivel", "nombre", "valor_min", "valor_max", "descripcion", "orden"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def web_guardar_escala(niveles):
    """Actualiza los rangos de la escala de valoración.

    niveles: list[dict] con keys id_nivel, nombre, valor_min, valor_max, descripcion.
    Valida que los rangos cubran de 0 a max_superior sin huecos ni solapamientos.
    Retorna (bool, mensaje).
    """
    if not niveles:
        return False, "Debe definir al menos un nivel."
    ordered = sorted(niveles, key=lambda n: float(n["valor_min"]))
    for n in ordered:
        if float(n["valor_min"]) >= float(n["valor_max"]):
            return False, f"El nivel '{n['nombre']}': el mínimo debe ser menor que el máximo."
    # Verificar solapamientos
    for i in range(len(ordered) - 1):
        if float(ordered[i]["valor_max"]) > float(ordered[i + 1]["valor_min"]):
            return (
                False,
                f"Los niveles '{ordered[i]['nombre']}' y '{ordered[i+1]['nombre']}' "
                "se solapan. Ajuste los rangos."
            )
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos."
    try:
        with con.cursor() as cur:
            for idx, n in enumerate(ordered, start=1):
                cur.execute(
                    """
                    UPDATE escala_valoracion
                    SET nombre=%s, valor_min=%s, valor_max=%s, descripcion=%s, orden=%s
                    WHERE id_nivel=%s;
                    """,
                    (n["nombre"], n["valor_min"], n["valor_max"],
                     n.get("descripcion", ""), idx, n["id_nivel"])
                )
        con.commit()
        return True, "Escala de valoración actualizada correctamente."
    except Exception as e:
        con.rollback()
        return False, f"Error al guardar: {e}"
    finally:
        con.close()


def web_nivel_para_valor(valor, escala=None):
    """Dado un valor numérico retorna (id_nivel, nombre_nivel) o ('', '') si no aplica."""
    if escala is None:
        escala = web_obtener_escala()
    for n in escala:
        if float(n["valor_min"]) <= float(valor) <= float(n["valor_max"]):
            return n["id_nivel"], n["nombre"]
    return "", "Sin definir"


# ==========================================
# 📊 CALIFICACIONES
# ==========================================

def web_obtener_estudiantes_por_curso(id_curso, ano_lectivo):
    """Retorna lista de dicts con los estudiantes matriculados en un curso/año."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT m.id_matricula, e.id_estudiante,
                       e.primer_nombre || ' ' || COALESCE(e.segundo_nombre,'') || ' ' ||
                       e.primer_apellido || ' ' || COALESCE(e.segundo_apellido,'') AS nombre_completo,
                       e.numero_documento
                FROM matriculas m
                JOIN estudiantes e ON e.id_estudiante = m.id_estudiante
                WHERE m.id_curso = %s AND m.ano_lectivo = %s AND m.estado = 'ACTIVO'
                ORDER BY e.primer_apellido, e.primer_nombre;
                """,
                (id_curso, ano_lectivo)
            )
            cols = ["id_matricula", "id_estudiante", "nombre_completo", "numero_documento"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return []
    finally:
        con.close()


def web_obtener_calificaciones(id_curso, ano_lectivo, numero_periodo, id_asignatura):
    """Retorna dict {id_matricula: {valor, observacion, id_calificacion}} para el filtro dado."""
    con = obtener_conexion_directa()
    if not con:
        return {}
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT c.id_matricula, c.valor, c.observacion, c.id_calificacion
                FROM calificaciones c
                JOIN matriculas m ON m.id_matricula = c.id_matricula
                WHERE m.id_curso = %s
                  AND c.ano_lectivo = %s
                  AND c.numero_periodo = %s
                  AND c.id_asignatura = %s;
                """,
                (id_curso, ano_lectivo, numero_periodo, id_asignatura)
            )
            return {
                row[0]: {
                    "valor": float(row[1]) if row[1] is not None else None,
                    "observacion": row[2] or "",
                    "id_calificacion": row[3]
                }
                for row in cur.fetchall()
            }
    except Exception:
        return {}
    finally:
        con.close()


def web_guardar_calificaciones_bulk(registros):
    """Guarda/actualiza un lote de calificaciones en una transacción.

    registros: list[dict] con keys:
        id_matricula (int), id_asignatura, numero_periodo, ano_lectivo,
        valor (float), observacion (str, opcional).
    Retorna (bool, mensaje, n_guardados).
    """
    if not registros:
        return True, "No hay registros que guardar.", 0
    con = obtener_conexion_directa()
    if not con:
        return False, "No fue posible conectar con la base de datos.", 0
    try:
        with con.cursor() as cur:
            n = 0
            for r in registros:
                if r.get("valor") is None:
                    continue  # Saltar filas sin nota
                cur.execute(
                    """
                    INSERT INTO calificaciones
                        (id_calificacion, id_matricula, id_asignatura,
                         numero_periodo, ano_lectivo, valor, observacion)
                    VALUES (
                        COALESCE(
                            (SELECT id_calificacion FROM calificaciones
                             WHERE id_matricula=%s AND id_asignatura=%s AND numero_periodo=%s),
                            'CAL-' || LPAD(nextval('seq_id_calificacion')::TEXT, 5, '0')
                        ),
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id_matricula, id_asignatura, numero_periodo) DO UPDATE SET
                        valor       = EXCLUDED.valor,
                        observacion = EXCLUDED.observacion,
                        fecha_registro = now();
                    """,
                    (
                        r["id_matricula"], r["id_asignatura"], r["numero_periodo"],
                        r["id_matricula"], r["id_asignatura"],
                        r["numero_periodo"], r["ano_lectivo"],
                        r["valor"], r.get("observacion", "")
                    )
                )
                n += 1
        con.commit()
        return True, f"{n} calificación(es) guardada(s) correctamente.", n
    except Exception as e:
        con.rollback()
        return False, f"Error al guardar: {e}", 0
    finally:
        con.close()


# ==========================================
# 📄 BOLETÍN — DATOS DE APOYO
# ==========================================

def web_guardar_boletin_datos(id_matricula, numero_periodo, inasistencias, observaciones):
    """Upsert de inasistencias y observaciones. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "Sin conexión."
    try:
        with con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO boletin_datos (id_matricula, numero_periodo, inasistencias, observaciones)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_matricula, numero_periodo) DO UPDATE SET
                    inasistencias = EXCLUDED.inasistencias,
                    observaciones = EXCLUDED.observaciones;
                """,
                (id_matricula, numero_periodo, int(inasistencias), observaciones or "")
            )
        con.commit()
        return True, "Datos de boletín guardados."
    except Exception as e:
        con.rollback()
        return False, f"Error: {e}"
    finally:
        con.close()


def web_obtener_boletin_datos(id_matricula, numero_periodo):
    """Retorna dict {inasistencias, observaciones} o valores por defecto."""
    con = obtener_conexion_directa()
    if not con:
        return {"inasistencias": 0, "observaciones": ""}
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT inasistencias, observaciones FROM boletin_datos "
                "WHERE id_matricula=%s AND numero_periodo=%s;",
                (id_matricula, numero_periodo)
            )
            row = cur.fetchone()
        if row:
            return {"inasistencias": row[0], "observaciones": row[1] or ""}
        return {"inasistencias": 0, "observaciones": ""}
    except Exception:
        return {"inasistencias": 0, "observaciones": ""}
    finally:
        con.close()


def web_datos_para_boletin(id_matricula, numero_periodo, ano_lectivo):
    """Ensambla todos los datos necesarios para generar el boletín de un estudiante.

    Retorna dict completo o None si el estudiante no se encuentra.
    """
    con = obtener_conexion_directa()
    if not con:
        return None
    try:
        with con.cursor() as cur:
            # ── Estudiante + curso + grado ────────────────────────────────────
            cur.execute(
                """
                SELECT e.primer_nombre, e.segundo_nombre,
                       e.primer_apellido, e.segundo_apellido,
                       g.nombre_grado, g.nivel, g.id_grado,
                       m.id_curso
                FROM matriculas m
                JOIN estudiantes e ON e.id_estudiante = m.id_estudiante
                JOIN cursos      c ON c.id_curso       = m.id_curso
                JOIN grados      g ON g.id_grado       = c.id_grado
                WHERE m.id_matricula = %s AND m.ano_lectivo = %s;
                """,
                (id_matricula, ano_lectivo)
            )
            row = cur.fetchone()
            if not row:
                return None

            pn, sn, pa, sa, nombre_grado, nivel, id_grado, id_curso = row
            nombre_completo = " ".join(p for p in [pn, sn, pa, sa] if p).upper()

            # ── Director de grupo ─────────────────────────────────────────────
            cur.execute(
                """
                SELECT p.nombres || ' ' || p.apellidos
                FROM direcciones_grupo dg
                JOIN personal p ON p.id_personal = dg.id_personal
                WHERE dg.id_curso=%s AND dg.ano_lectivo=%s
                LIMIT 1;
                """,
                (id_curso, ano_lectivo)
            )
            dir_row = cur.fetchone()
            director = dir_row[0] if dir_row else ""

            # ── Asignaturas del plan de estudio del grado ─────────────────────
            cur.execute(
                """
                SELECT a.id_asignatura, a.nombre
                FROM plan_estudio pe
                JOIN asignaturas a ON a.id_asignatura = pe.id_asignatura
                WHERE pe.id_grado = %s
                ORDER BY a.area_conocimiento, a.nombre;
                """,
                (id_grado,)
            )
            asignaturas = cur.fetchall()  # [(id, nombre), ...]

            # ── Indicadores y calificaciones por asignatura ───────────────────
            asig_data = []
            notas_para_promedio = []
            for id_asig, nom_asig in asignaturas:
                # Indicadores
                cur.execute(
                    """
                    SELECT descripcion FROM indicadores_desempeno
                    WHERE ano_lectivo=%s AND id_grado=%s
                      AND id_asignatura=%s AND numero_periodo=%s
                    ORDER BY tipo, id_indicador;
                    """,
                    (ano_lectivo, id_grado, id_asig, numero_periodo)
                )
                indicadores = [r[0] for r in cur.fetchall()]

                # Nota
                cur.execute(
                    """
                    SELECT valor FROM calificaciones
                    WHERE id_matricula=%s AND id_asignatura=%s AND numero_periodo=%s;
                    """,
                    (id_matricula, id_asig, numero_periodo)
                )
                cal_row = cur.fetchone()
                nota = float(cal_row[0]) if cal_row else None

                if nota is not None:
                    notas_para_promedio.append(nota)

                asig_data.append({
                    "id_asignatura": id_asig,
                    "nombre":        nom_asig,
                    "indicadores":   indicadores,
                    "nota":          nota,
                })

            # ── Datos del boletín (inasistencias + observaciones) ─────────────
            cur.execute(
                "SELECT inasistencias, observaciones FROM boletin_datos "
                "WHERE id_matricula=%s AND numero_periodo=%s;",
                (id_matricula, numero_periodo)
            )
            bd_row = cur.fetchone()
            inasistencias = bd_row[0] if bd_row else 0
            observaciones = bd_row[1] if bd_row else ""

        promedio = round(sum(notas_para_promedio) / len(notas_para_promedio), 2) \
                   if notas_para_promedio else None

        return {
            "nombre_completo": nombre_completo,
            "nombre_grado":    nombre_grado,
            "nivel":           nivel,          # PREESCOLAR / PRIMARIA / BACHILLERATO
            "id_grado":        id_grado,
            "asignaturas":     asig_data,
            "inasistencias":   inasistencias,
            "observaciones":   observaciones,
            "promedio":        promedio,
            "director":        director,
        }
    except Exception as e:
        return None
    finally:
        con.close()




def web_obtener_promedios_periodo(ids_matricula, numero_periodo):
    """Retorna dict {id_matricula: promedio_float} en una sola consulta."""
    if not ids_matricula:
        return {}
    con = obtener_conexion_directa()
    if not con:
        return {}
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_matricula, ROUND(AVG(valor)::numeric, 2) "
                "FROM calificaciones "
                "WHERE numero_periodo = %s AND id_matricula = ANY(%s) "
                "GROUP BY id_matricula;",
                (numero_periodo, list(ids_matricula))
            )
            return {r[0]: float(r[1]) for r in cur.fetchall()}
    except Exception:
        return {}
    finally:
        con.close()


def web_obtener_boletin_datos_bulk(ids_matricula, numero_periodo):
    """Retorna dict {id_matricula: {inasistencias, observaciones}} en una consulta."""
    if not ids_matricula:
        return {}
    con = obtener_conexion_directa()
    if not con:
        return {}
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_matricula, inasistencias, observaciones "
                "FROM boletin_datos "
                "WHERE numero_periodo = %s AND id_matricula = ANY(%s);",
                (numero_periodo, list(ids_matricula))
            )
            return {r[0]: {"inasistencias": r[1], "observaciones": r[2] or ""}
                    for r in cur.fetchall()}
    except Exception:
        return {}
    finally:
        con.close()


# ==========================================
# 📚 GRADOS — CRUD COMPLETO
# ==========================================

def web_obtener_grados_completo():
    """Retorna lista de dicts con id_grado, nombre_grado, nivel, orden."""
    con = obtener_conexion_directa()
    if not con:
        return []
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id_grado, nombre_grado, nivel, orden FROM grados "
                "ORDER BY CASE nivel "
                "  WHEN 'PREESCOLAR' THEN 1 WHEN 'PRIMARIA' THEN 2 "
                "  WHEN 'SECUNDARIA' THEN 3 WHEN 'MEDIA' THEN 4 ELSE 5 END, "
                "orden, nombre_grado;"
            )
            cols = ["id_grado", "nombre_grado", "nivel", "orden"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        con.close()


def _siguiente_id_grado(cur):
    """Genera el siguiente ID disponible de la forma GRA-NN."""
    cur.execute(
        r"""
        SELECT COALESCE(MAX(CAST(REGEXP_REPLACE(id_grado, '[^0-9]', '', 'g') AS INTEGER)), 11) + 1
        FROM grados
        WHERE id_grado ~ '^GRA-[0-9]+$';
        """
    )
    num = cur.fetchone()[0]
    return f"GRA-{num:02d}"


def web_registrar_grado(nombre_grado, nivel, orden):
    """Crea un nuevo grado. Retorna (bool, mensaje, id_grado|None)."""
    if nivel not in ("PREESCOLAR", "PRIMARIA", "SECUNDARIA", "MEDIA"):
        return False, "Nivel inválido.", None
    if not nombre_grado.strip():
        return False, "El nombre del grado es obligatorio.", None
    con = obtener_conexion_directa()
    if not con:
        return False, "Sin conexión.", None
    try:
        with con.cursor() as cur:
            # Verificar nombre duplicado
            cur.execute(
                "SELECT 1 FROM grados WHERE LOWER(nombre_grado)=LOWER(%s);",
                (nombre_grado.strip(),)
            )
            if cur.fetchone():
                return False, f"Ya existe un grado con el nombre '{nombre_grado}'.", None
            id_grado = _siguiente_id_grado(cur)
            cur.execute(
                "INSERT INTO grados (id_grado, nombre_grado, nivel, orden) VALUES (%s,%s,%s,%s);",
                (id_grado, nombre_grado.strip(), nivel, int(orden))
            )
        con.commit()
        return True, f"Grado '{nombre_grado}' registrado con ID {id_grado}.", id_grado
    except Exception as e:
        con.rollback()
        return False, f"Error: {e}", None
    finally:
        con.close()


def web_actualizar_grado(id_grado, nombre_grado, nivel, orden):
    """Actualiza nombre, nivel y orden de un grado existente. Retorna (bool, mensaje)."""
    if nivel not in ("PREESCOLAR", "PRIMARIA", "SECUNDARIA", "MEDIA"):
        return False, "Nivel inválido."
    if not nombre_grado.strip():
        return False, "El nombre del grado es obligatorio."
    con = obtener_conexion_directa()
    if not con:
        return False, "Sin conexión."
    try:
        with con.cursor() as cur:
            # Verificar nombre duplicado en otro grado
            cur.execute(
                "SELECT 1 FROM grados WHERE LOWER(nombre_grado)=LOWER(%s) AND id_grado<>%s;",
                (nombre_grado.strip(), id_grado)
            )
            if cur.fetchone():
                return False, f"Ya existe otro grado con el nombre '{nombre_grado}'."
            cur.execute(
                "UPDATE grados SET nombre_grado=%s, nivel=%s, orden=%s WHERE id_grado=%s;",
                (nombre_grado.strip(), nivel, int(orden), id_grado)
            )
        con.commit()
        return True, f"Grado '{nombre_grado}' actualizado correctamente."
    except Exception as e:
        con.rollback()
        return False, f"Error: {e}"
    finally:
        con.close()


def web_eliminar_grado(id_grado):
    """Elimina un grado si no tiene cursos, indicadores ni plan de estudio. Retorna (bool, mensaje)."""
    con = obtener_conexion_directa()
    if not con:
        return False, "Sin conexión."
    try:
        with con.cursor() as cur:
            # Verificar dependencias
            for tabla, col in [("cursos","id_grado"),("plan_estudio","id_grado"),("indicadores_desempeno","id_grado")]:
                cur.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {col}=%s;", (id_grado,))
                cnt = cur.fetchone()[0]
                if cnt > 0:
                    nombres = {"cursos":"curso(s)","plan_estudio":"asignatura(s) en plan de estudio",
                               "indicadores_desempeno":"indicador(es)"}
                    return False, (f"No se puede eliminar: tiene {cnt} {nombres[tabla]} asociado(s). "
                                   "Elimínelos primero.")
            cur.execute("DELETE FROM grados WHERE id_grado=%s;", (id_grado,))
        con.commit()
        return True, "Grado eliminado correctamente."
    except Exception as e:
        con.rollback()
        return False, f"Error: {e}"
    finally:
        con.close()

def autenticar_usuario(usuario, password):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        cur.execute("""
            SELECT
                id_usuario,
                usuario,
                password_hash,
                rol,
                estado,
                ultimo_acceso
            FROM usuarios
            WHERE usuario=%s
        """, (usuario,))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if resultado is None:
            return False, "Usuario o contraseña incorrectos."

        if resultado[4] == "INACTIVO":
            return False, "Su usuario se encuentra inactivo. Comuníquese con el administrador."

        password_hash = resultado[2]

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        ):
            return False, "Usuario o contraseña incorrectos."

        return True, (
            resultado[0],   # id_usuario
            resultado[1],   # usuario
            resultado[3],   # rol
            resultado[4],   # estado
            resultado[5]    # ultimo_acceso
        )

    except Exception as e:

        print(e)

        if conn:
            conn.close()

        return False, "Error interno del sistema."    

def actualizar_ultimo_acceso(id_usuario):
    """
    Actualiza la fecha y hora del último acceso del usuario.
    """

    conn = obtener_conexion_directa()

    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE usuarios
                SET ultimo_acceso = CURRENT_TIMESTAMP
                WHERE id_usuario = %s
            """, (id_usuario,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()

def obtener_usuarios():
    """
    Retorna todos los usuarios registrados.
    """

    conn = obtener_conexion_directa()

    if conn is None:
        return []

    try:

        cur = conn.cursor()

        cur.execute("""
            SELECT
                id_usuario,
                usuario,
                rol,
                estado,
                ultimo_acceso
            FROM usuarios
            ORDER BY usuario;
        """)

        datos = cur.fetchall()

        cur.close()
        conn.close()

        return datos

    except Exception as e:

        print(e)

        if conn:
            conn.close()

        return []
    
def crear_usuario(usuario, password_hash, rol, estado):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        # Verificar si el usuario ya existe
        cur.execute("""
            SELECT 1
            FROM usuarios
            WHERE UPPER(usuario) = UPPER(%s)
        """, (usuario,))

        if cur.fetchone():

            cur.close()
            conn.close()

            return False, "Ya existe un usuario con ese nombre."

        # Crear usuario
        cur.execute("""
            INSERT INTO usuarios
            (
                usuario,
                password_hash,
                rol,
                estado
            )
            VALUES (%s, %s, %s, %s)
        """, (
            usuario,
            password_hash,
            rol,
            estado
        ))

        conn.commit()

        cur.close()
        conn.close()

        return True, "Usuario creado correctamente."

    except Exception as e:

        conn.rollback()
        conn.close()

        return False, str(e)
    
def actualizar_usuario(id_usuario, usuario, rol, estado):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        # Validar nombre de usuario duplicado
        cur.execute("""
            SELECT id_usuario
            FROM usuarios
            WHERE LOWER(usuario)=LOWER(%s)
              AND id_usuario<>%s
        """, (
            usuario,
            id_usuario
        ))

        if cur.fetchone():

            cur.close()
            conn.close()

            return False, "Ya existe un usuario con ese nombre."

        # Obtener datos actuales del usuario
        cur.execute("""
            SELECT rol, estado
            FROM usuarios
            WHERE id_usuario=%s
        """, (id_usuario,))

        actual = cur.fetchone()

        # Si es ADMIN, verificar que no sea el último administrador activo
        # Si el usuario actualmente es ADMIN y ACTIVO,
# verificar que no quede el sistema sin administradores activos.

        if actual[0] == "ADMIN" and actual[1] == "ACTIVO":

            cur.execute("""
                SELECT COUNT(*)
                FROM usuarios
                WHERE rol = 'ADMIN'
                AND estado = 'ACTIVO'
                AND id_usuario <> %s
            """, (id_usuario,))

            otros_admin = cur.fetchone()[0]

            if otros_admin == 0:

                if rol != "ADMIN":

                    cur.close()
                    conn.close()

                    return False, (
                        "No puede cambiar el rol del único administrador activo."
                    )

                if estado != "ACTIVO":

                    cur.close()
                    conn.close()

                    return False, (
                        "No puede inactivar el único administrador activo."
                    )

        # Actualizar usuario
        cur.execute("""
            UPDATE usuarios
            SET
                usuario=%s,
                rol=%s,
                estado=%s
            WHERE id_usuario=%s
        """, (
            usuario,
            rol,
            estado,
            id_usuario
        ))

        conn.commit()

        cur.close()
        conn.close()

        return True, "Usuario actualizado correctamente."

    except Exception as e:

        conn.rollback()

        if conn:
            conn.close()

        return False, str(e)
    
def cambiar_password_usuario(id_usuario, password_hash):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        cur.execute("""
            UPDATE usuarios
            SET password_hash=%s
            WHERE id_usuario=%s
        """, (
            password_hash,
            id_usuario
        ))

        conn.commit()

        cur.close()
        conn.close()

        return True, "Contraseña actualizada correctamente."

    except Exception as e:

        conn.rollback()

        if conn:
            conn.close()

        return False, str(e)
    
def cambiar_estado_usuario(id_usuario):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        # Obtener datos del usuario
        cur.execute("""
            SELECT rol, estado
            FROM usuarios
            WHERE id_usuario=%s
        """, (id_usuario,))

        usuario = cur.fetchone()

        if usuario is None:

            cur.close()
            conn.close()

            return False, "El usuario no existe."

        # Si es el único ADMIN ACTIVO, no permitir inactivarlo
        if usuario[0] == "ADMIN" and usuario[1] == "ACTIVO":

            cur.execute("""
                SELECT COUNT(*)
                FROM usuarios
                WHERE rol='ADMIN'
                  AND estado='ACTIVO'
                  AND id_usuario<>%s
            """, (id_usuario,))

            otros_admin = cur.fetchone()[0]

            if otros_admin == 0:

                cur.close()
                conn.close()

                return False, (
                    "No puede inactivar el único administrador activo del sistema."
                )

        # Cambiar estado
        cur.execute("""
            UPDATE usuarios
            SET estado =
                CASE
                    WHEN estado='ACTIVO' THEN 'INACTIVO'
                    ELSE 'ACTIVO'
                END
            WHERE id_usuario=%s
        """, (id_usuario,))

        conn.commit()

        cur.close()
        conn.close()

        return True, "Estado actualizado correctamente."

    except Exception as e:

        conn.rollback()

        if conn:
            conn.close()

        return False, str(e)    
def restablecer_password_usuario(id_usuario, password_hash):

    conn = obtener_conexion_directa()

    if conn is None:
        return False, "No fue posible conectar con la base de datos."

    try:

        cur = conn.cursor()

        cur.execute("""
            UPDATE usuarios
            SET password_hash=%s
            WHERE id_usuario=%s
        """, (
            password_hash,
            id_usuario
        ))

        conn.commit()

        cur.close()
        conn.close()

        return True, "Contraseña restablecida correctamente."

    except Exception as e:

        conn.rollback()

        if conn:
            conn.close()

        return False, str(e)
