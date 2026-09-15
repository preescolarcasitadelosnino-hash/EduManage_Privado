import base64
import binascii
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

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
)


SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveManager:
    """Gestiona Google Drive sin bloquear el arranque de Streamlit Cloud."""

    def __init__(self):
        self.service = None
        self.root_folder = st.secrets.get("GOOGLE_DRIVE_ROOT", "")
        self.autenticar()

    def autenticar(self):
        """Carga credenciales desde Secrets o desde archivos locales.

        En Streamlit Cloud no intenta abrir un navegador. Si las credenciales
        no están configuradas, el resto de EduManager puede iniciar y las
        operaciones de Drive mostrarán un error claro cuando se soliciten.
        """
        creds = None

        service_account_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        service_account_json_b64 = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        if service_account_json or service_account_json_b64:
            try:
                if service_account_json_b64:
                    decoded_json = base64.b64decode(
                        str(service_account_json_b64),
                        validate=True,
                    ).decode("utf-8")
                    service_account_info = json.loads(decoded_json)
                else:
                    service_account_info = (
                        json.loads(service_account_json)
                        if isinstance(service_account_json, str)
                        else dict(service_account_json)
                    )
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=SCOPES,
                )
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                binascii.Error,
                json.JSONDecodeError,
            ):
                creds = None

        token_json = st.secrets.get("GOOGLE_TOKEN_JSON")
        if creds is None and token_json:
            try:
                token_info = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            except (TypeError, ValueError, json.JSONDecodeError):
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
            permitir_oauth_local = st.secrets.get("GOOGLE_ALLOW_LOCAL_OAUTH", True)
            if permitir_oauth_local and Path(GOOGLE_DESKTOP_CLIENT).exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(GOOGLE_DESKTOP_CLIENT),
                        SCOPES,
                    )
                    creds = flow.run_local_server(port=0)
                    Path(GOOGLE_TOKEN).parent.mkdir(parents=True, exist_ok=True)
                    Path(GOOGLE_TOKEN).write_text(creds.to_json(), encoding="utf-8")
                except Exception:
                    creds = None

        if not creds or not creds.valid:
            self.service = None
            return False

        self.service = build("drive", "v3", credentials=creds)
        return True

    def _require_service(self):
        if self.service is None:
            raise RuntimeError(
                "Google Drive no está configurado. Configure GOOGLE_TOKEN_JSON "
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
        ).execute()

    def buscar_carpeta(self, nombre_carpeta, carpeta_padre=None):
        service = self._require_service()
        padre = carpeta_padre or self.root_folder
        consulta = (
            f"name='{nombre_carpeta}' "
            "and mimeType='application/vnd.google-apps.folder' "
            f"and '{padre}' in parents "
            "and trashed=false"
        )
        resultados = service.files().list(
            q=consulta,
            fields="files(id,name)",
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
            ).execute()
            archivo = service.files().get(
                fileId=archivo["id"],
                fields="id,webViewLink,webContentLink",
            ).execute()
            return f"https://drive.google.com/uc?id={archivo['id']}&export=view"
        finally:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
