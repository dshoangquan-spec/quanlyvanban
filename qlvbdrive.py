# qlvbdrive.py
import os
import io
import json
import tempfile
from datetime import date, datetime

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# =========================
# Cấu hình trang + CSS
# =========================
st.set_page_config(page_title="Quản lý Văn bản - Google Drive + Sheets", layout="wide")
st.markdown(
    """
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.stTextInput>div>div>input, .stMultiSelect div[data-baseweb="select"] { min-height: 42px; }
.stButton>button { padding: 0.35rem 0.7rem; border-radius: 8px; font-size: 0.9rem; }
.btn-cell .stButton>button { padding: 0.25rem 0.55rem; font-size: 0.85rem; }
.stDataFrame, .stTable { font-size: 0.92rem; }
.badge { background:#eef3ff; color:#2c3e50; padding:2px 8px; border-radius:999px; font-size:.8rem; }
hr { margin: 0.6rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📚 Quản lý Văn bản — Google Drive + Google Sheets")


# =========================
# Đọc secrets
# =========================
def _get_secret(key: str):
    v = st.secrets.get(key)
    if not v:
        raise KeyError(f"Thiếu key `{key}` trong secrets.")
    return v


GOOGLE_CREDENTIALS = _get_secret("GOOGLE_CREDENTIALS")
SHEET_ID = _get_secret("SHEET_ID")
FOLDER_ID = _get_secret("FOLDER_ID")


# =========================
# Google API Clients
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_creds():
    creds_info = json.loads(GOOGLE_CREDENTIALS)
    return service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

@st.cache_resource(show_spinner=False)
def drive_service():
    return build("drive", "v3", credentials=get_creds())

@st.cache_resource(show_spinner=False)
def sheets_service():
    return build("sheets", "v4", credentials=get_creds())


# =========================
# Helpers
# =========================
def to_vn_date(d: date) -> str:
    """date -> dd/mm/yyyy"""
    return d.strftime("%d/%m/%Y")

def upload_to_drive(folder_id: str, file_path: str, file_name: str):
    """
    Upload 1 file vào thư mục Drive.
    Trả về: file_id, webViewLink.
    """
    service = drive_service()

    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    file_id = created["id"]

    # Cho phép Anyone with the link -> view
    try:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
    except Exception:
        pass  # nếu quyền đã đủ thì bỏ qua

    # Lấy lại link
    meta = service.files().get(fileId=file_id, fields="webViewLink").execute()
    return file_id, meta.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")


def append_row_to_sheet(sheet_id: str, row_values: list):
    """
    Ghi 1 dòng vào Google Sheets (append cuối bảng)
    """
    service = sheets_service()
    body = {"values": [row_values]}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def read_sheet(sheet_id: str) -> pd.DataFrame:
    """
    Đọc toàn bộ dữ liệu từ Sheet, trả về DataFrame với header dòng 1
    """
    service = sheets_service()
    res = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range="A1:Z10000"
    ).execute()
    values = res.get("values", [])
    if not values:
        return pd.DataFrame(columns=["Số văn bản", "Tên văn bản", "Ngày ban hành", "Cơ quan ban hành", "Link", "FileID"])

    header = values[0]
    rows = values[1:]
    return pd.DataFrame(rows, columns=header)


# =========================
# Form nhập liệu + upload
# =========================
with st.form("form_vanban", clear_on_submit=False):
    cL, cR = st.columns([2, 1])

    with cL:
        so_vb   = st.text_input("Số văn bản")
        ten_vb  = st.text_input("Tên văn bản")
        cq_bh   = st.text_input("Cơ quan ban hành")
        ngay_bh = st.date_input("Ngày ban hành", value=date.today(), format="DD/MM/YYYY")

    with cR:
        st.markdown("**Đính kèm (PDF/DOC/DOCX/XLS/XLSX …)**")
        file_upload = st.file_uploader("", type=None)
        st.caption("💡 Kéo–thả file vào đây. Dung lượng ≤ 200MB / tệp.")

    submitted = st.form_submit_button("💾 Lưu văn bản", type="primary")

    if submitted:
        if not file_upload:
            st.error("Vui lòng chọn file đính kèm.")
        else:
            # Lưu tạm rồi upload
            suffix = os.path.splitext(file_upload.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_upload.read())
                tmp_path = tmp.name

            try:
                file_id, web_link = upload_to_drive(FOLDER_ID, tmp_path, file_upload.name)
                # Ghi dòng vào Google Sheet theo đúng thứ tự cột:
                # Số văn bản | Tên văn bản | Ngày ban hành | Cơ quan ban hành | Link | FileID
                row = [
                    so_vb.strip(),
                    ten_vb.strip(),
                    to_vn_date(ngay_bh),
                    cq_bh.strip(),
                    web_link,
                    file_id,
                ]
                append_row_to_sheet(SHEET_ID, row)
                st.success("✅ Đã upload & ghi vào Google Sheets!")
                st.toast("Hoàn tất!", icon="✅")
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


st.markdown("---")
st.subheader("🗂️ Danh sách văn bản (đọc từ Google Sheets)")

# Đọc và hiển thị bảng
try:
    df = read_sheet(SHEET_ID)
except Exception as e:
    st.error(f"Không đọc được Google Sheets: {e}")
    df = pd.DataFrame(columns=["Số văn bản", "Tên văn bản", "Ngày ban hành", "Cơ quan ban hành", "Link", "FileID"])

# Tìm kiếm cơ bản
kw = st.text_input("🔎 Tìm kiếm", placeholder="Nhập số văn bản, tên văn bản, cơ quan…")
show = df.copy()
if kw:
    k = kw.strip().lower()
    show = show[show.apply(lambda r: any(k in str(x).lower() for x in r), axis=1)]

# Hiển thị
st.dataframe(show, use_container_width=True)

# Export CSV nhanh
if not show.empty:
    csv_bytes = show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Tải CSV", data=csv_bytes, file_name="quanly_vanban.csv", mime="text/csv")
