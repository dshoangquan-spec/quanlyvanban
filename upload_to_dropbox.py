import dropbox
import os
import streamlit as st

def upload_file_to_dropbox(file_path, file_name, dropbox_folder=""):
    TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]
    dbx = dropbox.Dropbox(TOKEN)

    dropbox_path = f"/{dropbox_folder}/{file_name}" if dropbox_folder else f"/{file_name}"

    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    return shared_link_metadata.url.replace("?dl=0", "?raw=1")
