import dropbox
import streamlit as st
import os

# Nhập Access Token (hoặc dùng st.secrets)
DROPBOX_ACCESS_TOKEN = st.secrets["DROPBOX_TOKEN"]  # Hoặc gán trực tiếp

# Hàm upload
def upload_to_dropbox(file_path, dropbox_path):
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    return shared_link_metadata.url.replace("?dl=0", "?raw=1")  # Trả link xem trực tiếp

# Giao diện Streamlit
uploaded_file = st.file_uploader("Chọn file để upload", type=["pdf", "docx", "png", "jpg"])
if uploaded_file is not None:
    file_name = uploaded_file.name
    file_path = os.path.join("/tmp", file_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    dropbox_link = upload_to_dropbox(file_path, f"/{file_name}")
    st.success("Upload thành công!")
    st.markdown(f"[Xem file tại đây]({dropbox_link})")
