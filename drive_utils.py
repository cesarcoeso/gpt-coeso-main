
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# === CONFIGURAÇÃO ===
FOLDER_NAME = "banco-coeso"
DB_FILENAME = "auth.db"

# === AUTENTICAÇÃO ===
SERVICE_ACCOUNT_INFO = {
    "type": "service_account",
    "project_id": "coesopainel",
    "private_key_id": "cb5b74ae871e30c32adcf26a181005cb36dd1011",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDCaEsec3Djnonf
...
t8pdFdNlcsY49SvN8DzhN2FQ3Q==
-----END PRIVATE KEY-----""",
    "client_email": "painel-assistente-coeso@coesopainel.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token"
}

SCOPES = ["https://www.googleapis.com/auth/drive"]

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES)
service = build("drive", "v3", credentials=credentials)

def get_folder_id():
    results = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}'",
                                   spaces='drive', fields="files(id, name)").execute()
    folders = results.get("files", [])
    if not folders:
        raise FileNotFoundError(f"Pasta '{FOLDER_NAME}' não encontrada no Drive.")
    return folders[0]['id']

def download_db_from_drive():
    folder_id = get_folder_id()
    query = f"name='{DB_FILENAME}' and '{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if not files:
        return False
    file_id = files[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(DB_FILENAME, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return True

def upload_db_to_drive():
    folder_id = get_folder_id()
    query = f"name='{DB_FILENAME}' and '{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    file_metadata = {
        "name": DB_FILENAME,
        "parents": [folder_id]
    }
    media = MediaFileUpload(DB_FILENAME, resumable=True)

    if files:
        file_id = files[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media).execute()
