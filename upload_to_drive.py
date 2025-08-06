from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_file_to_drive(file_path, file_name, folder_id):
    # Xác thực qua file credentials.json
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Khởi tạo API client
    service = build('drive', 'v3', credentials=creds)

    # Cấu hình metadata của file
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    # Chuẩn bị upload
    media = MediaFileUpload(file_path, resumable=True)
    
    # Tạo file trên Google Drive
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')
    file_url = f'https://drive.google.com/file/d/0B85NRfuypJmeZWRYcXY3czdXcVk/view'
    return file_url
