import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Folder ID của bạn
FOLDER_ID = "0B85NRfuypJmeZWRYcXY3czdXcVk"  # giữ nguyên ID này

def upload_file_to_drive(file_path, file_name):
    SCOPES = ['https://www.googleapis.com/auth/drive']

    # Đọc credentials từ secrets
    creds_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": file_name,
        "parents": [FOLDER_ID]
    }

    media = MediaFileUpload(file_path, resumable=True)

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()

    file_id = uploaded_file.get("id")

    # Tạo quyền xem công khai
    permission = {
        "type": "anyone",
        "role": "reader"
    }
    service.permissions().create(fileId=file_id, body=permission).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

# Ví dụ chạy test trong Streamlit
st.title("Upload file lên Google Drive folder chia sẻ")

uploaded = st.file_uploader("Chọn file", type=["pdf", "docx", "xlsx"])
if uploaded:
    with open(uploaded.name, "wb") as f:
        f.write(uploaded.getbuffer())

    link = upload_file_to_drive(uploaded.name, uploaded.name)
    st.success(f"Upload thành công! [Mở file]({link})")
