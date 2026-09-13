import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections.abc import Mapping

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from backend.config import (
    GOOGLE_DESKTOP_CLIENT,
    GOOGLE_TOKEN,
    GOOGLE_DRIVE_ROOT,
    GOOGLE_CREDENTIALS,
    obtener_configuracion,
)


SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveManager:
    """Gestiona Google Drive sin bloquear el arranque de Streamlit Cloud."""

    def __init__(self):
        self.service = None
        self.root_folder = str(
            obtener_configuracion("GOOGLE_DRIVE_ROOT", GOOGLE_DRIVE_ROOT)
        ).strip()
        self.auth_mode = None
        self.autenticar()

    @staticmethod
    def _secreto_json(nombre):
        """Devuelve un secreto JSON como dict, tanto si llega como texto como tabla TOML."""
        valor = obtener_configuracion(nombre)
        if isinstance(valor, Mapping):
            return dict(valor)
        if isinstance(valor, str) and valor.strip():
            try:
                resultado = json.loads(valor)
                return resultado if isinstance(resultado, dict) else None
            except json.JSONDecodeError:
                return None
        return None

    def autenticar(self):
        """Carga credenciales desde Secrets o desde archivos locales.

        En Streamlit Cloud no intenta abrir un navegador. Si las credenciales
        no están configuradas, el resto de EduManager puede iniciar y las
        operaciones de Drive mostrarán un error claro cuando se soliciten.
        """
        creds = None

        # En un servidor es preferible una cuenta de servicio. La carpeta raíz
        # debe estar compartida con el correo de esa cuenta con permiso de editor.
        service_account_info = self._secreto_json("GOOGLE_SERVICE_ACCOUNT_JSON")
        if service_account_info:
            try:
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=SCOPES,
                )
                self.auth_mode = "service_account"
            except (TypeError, ValueError, KeyError):
                creds = None

        if creds is None and Path(GOOGLE_CREDENTIALS).exists():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(GOOGLE_CREDENTIALS),
                    scopes=SCOPES,
                )
                self.auth_mode = "service_account_file"
            except (TypeError, ValueError, OSError):
                creds = None

        token_json = obtener_configuracion("GOOGLE_TOKEN_JSON")
        if creds is None and token_json:
            try:
                token_info = (
                    dict(token_json)
                    if isinstance(token_json, Mapping)
                    else json.loads(token_json)
                )
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
                self.auth_mode = "oauth_token"
            except (TypeError, ValueError, json.JSONDecodeError):
                if self.auth_mode is None:
                    creds = None

        if creds is None and Path(GOOGLE_TOKEN).exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(GOOGLE_TOKEN),
                    SCOPES,
                )
            except Exception:
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            permitir_oauth_local = obtener_configuracion("GOOGLE_ALLOW_LOCAL_OAUTH", True)
            if permitir_oauth_local and Path(GOOGLE_DESKTOP_CLIENT).exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(GOOGLE_DESKTOP_CLIENT),
                        SCOPES,
                    )
                    creds = flow.run_local_server(port=0)
                    self.auth_mode = "oauth_local"
                    Path(GOOGLE_TOKEN).parent.mkdir(parents=True, exist_ok=True)
                    Path(GOOGLE_TOKEN).write_text(creds.to_json(), encoding="utf-8")
                except Exception:
                    creds = None

        if not creds or not creds.valid:
            self.service = None
            return False

        self.service = build("drive", "v3", credentials=creds)
        return True

    def probar_conexion(self):
        """Valida que la carpeta raíz exista y sea accesible con las credenciales."""
        service = self._require_service()
        if not self.root_folder:
            raise RuntimeError("GOOGLE_DRIVE_ROOT no está configurado.")
        return service.files().get(
            fileId=self.root_folder,
            fields="id,name,mimeType,trashed",
            supportsAllDrives=True,
        ).execute()

    def _require_service(self):
        if self.service is None:
            raise RuntimeError(
                "Google Drive no está configurado. Configure "
                "GOOGLE_SERVICE_ACCOUNT_JSON o GOOGLE_TOKEN_JSON "
                "en los Secrets de Streamlit."
            )
        return self.service

    def subir_archivo(self, archivo_local, nombre_archivo, carpeta_id=None):
        service = self._require_service()
        carpeta = carpeta_id or self.root_folder
        metadata = {"name": nombre_archivo, "parents": [carpeta]}
        media = MediaFileUpload(archivo_local, resumable=True)
        return service.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        ).execute()

    def subir_archivo_streamlit(
        self,
        archivo_streamlit,
        nombre_archivo,
        carpeta_id=None,
        hacer_publico=False,
    ):
        """Sube un archivo recibido desde Streamlit y devuelve una URL persistente."""
        extension = Path(archivo_streamlit.name).suffix
        with NamedTemporaryFile(delete=False, suffix=extension) as temp:
            temp.write(archivo_streamlit.getbuffer())
            ruta_temporal = temp.name

        try:
            archivo = self.subir_archivo(ruta_temporal, nombre_archivo, carpeta_id)
            if hacer_publico:
                self.service.permissions().create(
                    fileId=archivo["id"],
                    body={"type": "anyone", "role": "reader"},
                    supportsAllDrives=True,
                ).execute()
            return f"https://drive.google.com/uc?export=view&id={archivo['id']}"
        finally:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)

    def obtener_carpeta_institucion(self, nombre_institucion):
        self.probar_conexion()
        carpeta_institucion = self.crear_carpeta("INSTITUCION")
        nombre = str(nombre_institucion or "INSTITUCION").strip()
        return self.crear_carpeta(nombre, carpeta_institucion)

    def buscar_carpeta(self, nombre_carpeta, carpeta_padre=None):
        service = self._require_service()
        padre = carpeta_padre or self.root_folder
        nombre_consulta = (
            str(nombre_carpeta)
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        )
        consulta = (
            f"name='{nombre_consulta}' "
            "and mimeType='application/vnd.google-apps.folder' "
            f"and '{padre}' in parents "
            "and trashed=false"
        )
        resultados = service.files().list(
            q=consulta,
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        ).execute()
        carpetas = resultados.get("files", [])
        return carpetas[0]["id"] if carpetas else None

    def crear_carpeta(self, nombre_carpeta, carpeta_padre=None):
        service = self._require_service()
        padre = carpeta_padre or self.root_folder
        existente = self.buscar_carpeta(nombre_carpeta, padre)
        if existente:
            return existente
        metadata = {
            "name": nombre_carpeta,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [padre],
        }
        carpeta = service.files().create(
            body=metadata,
            fields="id,name",
            supportsAllDrives=True,
        ).execute()
        return carpeta["id"]

    def obtener_carpeta_estudiante(self, id_estudiante):
        carpeta_estudiantes = self.crear_carpeta("ESTUDIANTES")
        return self.crear_carpeta(id_estudiante, carpeta_estudiantes)

    def obtener_carpeta_acudiente(self, id_acudiente):
        carpeta_acudientes = self.crear_carpeta("ACUDIENTES")
        return self.crear_carpeta(id_acudiente, carpeta_acudientes)

    def subir_foto_estudiante(self, archivo_streamlit, id_estudiante):
        service = self._require_service()
        carpeta = self.obtener_carpeta_estudiante(id_estudiante)
        extension = Path(archivo_streamlit.name).suffix

        with NamedTemporaryFile(delete=False, suffix=extension) as temp:
            temp.write(archivo_streamlit.getbuffer())
            ruta_temporal = temp.name

        try:
            archivo = self.subir_archivo(
                ruta_temporal,
                f"FOTO_ESTUDIANTE{id_estudiante}{extension}",
                carpeta,
            )
            service.permissions().create(
                fileId=archivo["id"],
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True,
            ).execute()
            archivo = service.files().get(
                fileId=archivo["id"],
                fields="id,webViewLink,webContentLink",
            ).execute()
            return f"https://drive.google.com/uc?id={archivo['id']}&export=view"
        finally:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)

if __name__ == "__main__":
    print("Iniciando autenticación con Google Drive...")
    manager = DriveManager()
    if manager.service:
        print("¡Autenticación exitosa! El archivo token.json se ha creado correctamente.")
    else:
        print("No se pudo completar la autenticación.")
