import dropbox
import os
import streamlit as st

def upload_file_to_dropbox(file_path, file_name):
    TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]
    dbx = dropbox.Dropbox(TOKEN)

    # Đường dẫn cố định trong Dropbox (KHÔNG dùng dấu %20)
    dropbox_folder = "/Quan/Quan ly van ban/Van ban dieu hanh, chi dao"
    dropbox_path = f"{dropbox_folder}/{file_name}"

    # Upload file
    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    return f"✅ Đã upload thành công tới: {dropbox_path}"

