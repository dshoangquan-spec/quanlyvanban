import dropbox
import os
import streamlit as st

def upload_file_to_dropbox(file_path, file_name, dropbox_folder=""):
    TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]
    dbx = dropbox.Dropbox(TOKEN)

    # Tạo đường dẫn Dropbox
    dropbox_path = f"/{dropbox_folder}/{file_name}" if dropbox_folder else f"/{file_name}"

    # Upload file
    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    # ✅ Bỏ phần tạo link chia sẻ
    # Nếu cần đường dẫn tạm thời thì trả về dropbox_path
    return f"Đã upload: {dropbox_path}"
