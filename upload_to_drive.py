from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Gắn sẵn Folder ID của bạn
FOLDER_ID = "0B85NRfuypJmeZWRYcXY3czdXcVk"

def upload_file_to_drive(file_path, file_name):
    # Phạm vi sử dụng Google Drive
    SCOPES = ['https://www.googleapis.com/auth/drive']

   import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = "0B85NRfuypJmeZWRYcXY3czdXcVk"

def upload_file_to_drive(file_path, file_name):
    SCOPES = ['https://www.googleapis.com/auth/drive']

    # Tạo credentials từ secrets
    creds_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }

    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')

    # Cấp quyền công khai
    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=file_id, body=permission).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

    # Tạo dịch vụ Google Drive
    service = build('drive', 'v3', credentials=creds)

    # Metadata cho file mới
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }

    # Chuẩn bị file upload
    media = MediaFileUpload(file_path, resumable=True)

    # Tạo file trên Google Drive
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')

    # Cấp quyền xem công khai
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(fileId=file_id, body=permission).execute()

    # Trả về link xem file
    file_url = f"https://drive.google.com/file/d/{file_id}/view"
    return file_url
