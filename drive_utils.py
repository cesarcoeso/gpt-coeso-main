import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError

# === CONFIGURAÇÃO ===
FOLDER_NAME = "banco-coeso"
DB_FILENAME = "auth.db"

# === AUTENTICAÇÃO ===
try:
    # Carrega as credenciais do secrets.toml
    SERVICE_ACCOUNT_INFO = {
        "type": st.secrets["gdrive_service_account"]["type"],
        "project_id": st.secrets["gdrive_service_account"]["project_id"],
        "private_key_id": st.secrets["gdrive_service_account"]["private_key_id"],
        "private_key": st.secrets["gdrive_service_account"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["gdrive_service_account"]["client_email"],
        "token_uri": st.secrets["gdrive_service_account"]["token_uri"]
    }
    
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    credentials = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO, scopes=SCOPES)
    service = build("drive", "v3", credentials=credentials)

except Exception as e:
    st.error(f"Erro ao carregar credenciais do Google Drive: {str(e)}")
    raise

def get_folder_id():
    """Obtém o ID da pasta 'banco-coeso' no Google Drive pessoal"""
    try:
        # Primeiro verifica se a service account tem acesso à pasta
        results = service.files().list(
            q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        
        folders = results.get('files', [])
        
        if not folders:
            raise FileNotFoundError(
                f"Pasta '{FOLDER_NAME}' não encontrada. "
                f"Certifique-se que a pasta existe e está compartilhada com: {SERVICE_ACCOUNT_INFO['client_email']}"
            )
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
        
        # Busca o arquivo na pasta específica
        results = service.files().list(
            q=f"name='{DB_FILENAME}' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            st.warning(f"Arquivo {DB_FILENAME} não encontrado na pasta.")
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
        
        # Verifica se o arquivo já existe
        results = service.files().list(
            q=f"name='{DB_FILENAME}' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()
        
        files = results.get('files', [])
        file_metadata = {
            'name': DB_FILENAME,
            'parents': [folder_id]
        }
        media = MediaFileUpload(DB_FILENAME, mimetype='application/x-sqlite3')
        
        if files:
            # Atualiza arquivo existente
            file_id = files[0]['id']
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Cria novo arquivo
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
        return True
        
    except HttpError as error:
        st.error(f"Erro ao enviar arquivo: {error}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        return False
