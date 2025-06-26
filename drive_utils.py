import io
import os
import streamlit as st
import pickle

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError

# === CONFIGURAÇÕES ===
FOLDER_NAME = "banco-coeso"
DB_FILENAME = "auth.db"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = "token_drive.pkl"


@st.cache_resource
def get_drive_service():
    creds = None

    # Verifica se já existe token salvo em sessão
    if "token_drive" in st.session_state:
        creds = st.session_state["token_drive"]

    # Ou token salvo em disco (útil no desenvolvimento local)
    elif os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # Se não houver token válido, inicia fluxo de autenticação
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Configurações do secrets.toml
            client_config = {
                "installed": {
                    "client_id": st.secrets["gdrive_oauth"]["client_id"],
                    "client_secret": st.secrets["gdrive_oauth"]["client_secret"],
                    "auth_uri": st.secrets["gdrive_oauth"]["auth_uri"],
                    "token_uri": st.secrets["gdrive_oauth"]["token_uri"],
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                }
            }

            flow = Flow.from_client_config(client_config, SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"🔐 [Clique aqui para autorizar o app com sua conta Google]({auth_url})")
            auth_code = st.text_input("👉 Após autorizar, cole aqui o código:")

            if not auth_code:
                st.stop()

            try:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                st.session_state["token_drive"] = creds
                # Opcional: salva em disco também
                with open(TOKEN_FILE, "wb") as token:
                    pickle.dump(creds, token)
            except Exception as e:
                st.error(f"Erro ao autenticar com o Google: {e}")
                st.stop()

    return build("drive", "v3", credentials=creds)


# === INSTANCIA O SERVIÇO ===
try:
    service = get_drive_service()
except Exception as e:
    st.error(f"Erro na autenticação do Google Drive: {str(e)}")
    raise


# === FUNÇÕES DE UPLOAD E DOWNLOAD ===
def get_folder_id():
    """Obtém o ID da pasta 'banco-coeso' no Google Drive"""
    try:
        results = service.files().list(
            q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        folders = results.get('files', [])
        if not folders:
            raise FileNotFoundError(f"Pasta '{FOLDER_NAME}' não encontrada.")
        return folders[0]['id']
    except HttpError as error:
        st.error(f"Erro ao buscar pasta: {error}")
        raise
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        raise


def download_db_from_drive():
    """Faz download do banco de dados do Google Drive"""
    try:
        folder_id = get_folder_id()
        results = service.files().list(
            q=f"name='{DB_FILENAME}' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        files = results.get('files', [])
        if not files:
            st.warning(f"Arquivo {DB_FILENAME} não encontrado.")
            return False
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        with io.FileIO(DB_FILENAME, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return True
    except HttpError as error:
        st.error(f"Erro ao baixar arquivo: {error}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        return False


def upload_db_to_drive():
    """Faz upload do banco de dados para o Google Drive"""
    try:
        folder_id = get_folder_id()
        results = service.files().list(
            q=f"name='{DB_FILENAME}' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        files = results.get('files', [])
        file_metadata = {'name': DB_FILENAME, 'parents': [folder_id]}
        media = MediaFileUpload(DB_FILENAME, mimetype='application/x-sqlite3')
        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except HttpError as error:
        st.error(f"Erro ao enviar arquivo: {error}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        return False
