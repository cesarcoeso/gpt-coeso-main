import io
import os
import streamlit as st
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError

# === CONFIGURAÇÃO ===
FOLDER_NAME = "banco-coeso"
DB_FILENAME = "auth.db"
SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Permissão básica para leitura/escrita

# === AUTENTICAÇÃO COM OAUTH ===
@st.cache_resource
def get_drive_service():
    creds = None
    token_path = "token_drive.pkl"
    
    # Usa token salvo (login já feito anteriormente)
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # Se não tiver credenciais válidas, faz login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Salva o token para uso futuro
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build("drive", "v3", credentials=creds)

# Instancia o serviço
try:
    service = get_drive_service()
except Exception as e:
    st.error(f"Erro na autenticação do Google Drive: {str(e)}")
    raise

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
