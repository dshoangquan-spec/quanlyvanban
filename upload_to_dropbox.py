# upload_to_dropbox.py
import os
import dropbox
import streamlit as st
from dropbox import files as dbx_files
from dropbox.exceptions import ApiError

# Thư mục mặc định (đúng tên như trên Dropbox, không dùng %20)
DEFAULT_FOLDER = "/Quan/Quan ly van ban/Van ban dieu hanh, chi dao"


def _get_dbx() -> dropbox.Dropbox:
    """Khởi tạo client Dropbox từ secrets hoặc biến môi trường."""
    token = os.environ.get("DROPBOX_ACCESS_TOKEN") or st.secrets["DROPBOX_ACCESS_TOKEN"]
    return dropbox.Dropbox(token)


def _ensure_folder(dbx: dropbox.Dropbox, folder_path: str) -> None:
    """Tạo thư mục nếu chưa có (an toàn khi gọi lặp lại)."""
    if not folder_path or folder_path == "/":
        return
    try:
        dbx.files_get_metadata(folder_path)
    except ApiError as e:
        # Nếu không tồn tại -> tạo
        if "path/not_found" in str(e.error).lower():
            dbx.files_create_folder_v2(folder_path)
        else:
            raise


def upload_file_to_dropbox(file_path: str, file_name: str, dropbox_folder: str | None = None) -> str:
    """
    Upload file lên Dropbox.
    - dropbox_folder: nếu None sẽ dùng DEFAULT_FOLDER
    - Trả về: đường dẫn Dropbox (ví dụ: /Quan/.../tenfile.pdf)
    YÊU CẦU QUYỀN: files.content.write
    """
    dbx = _get_dbx()

    folder = (dropbox_folder or DEFAULT_FOLDER).strip()
    if not folder.startswith("/"):
        folder = "/" + folder
    folder = folder.rstrip("/")

    _ensure_folder(dbx, folder)

    dropbox_path = f"{folder}/{file_name}"

    with open(file_path, "rb") as f:
        dbx.files_upload(
            f.read(),
            dropbox_path,
            mode=dbx_files.WriteMode.overwrite,
            mute=True,
        )

    return dropbox_path


def download_bytes_from_dropbox(dropbox_path: str) -> bytes:
    """
    Tải file từ Dropbox và trả về bytes để dùng với st.download_button.
    YÊU CẦU QUYỀN: files.content.read
    """
    dbx = _get_dbx()
    try:
        _meta, res = dbx.files_download(dropbox_path)
        return res.content
    except ApiError as e:
        # Cho message dễ hiểu hơn khi path sai / không tồn tại
        raise RuntimeError(f"Không tải được file từ '{dropbox_path}': {e}")


def delete_file_from_dropbox(dropbox_path: str) -> None:
    """
    Xóa file trên Dropbox theo đường dẫn.
    YÊU CẦU QUYỀN: files.content.write
    """
    dbx = _get_dbx()
    try:
        dbx.files_delete_v2(dropbox_path)
    except ApiError as e:
        raise RuntimeError(f"Không xóa được file '{dropbox_path}': {e}")
