import json
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================
# Load config
# ==========================
SHEET_ID = st.secrets["SHEET_ID"]
FOLDER_ID = st.secrets["FOLDER_ID"]
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]

# ==========================
# Init Google API
# ==========================
creds_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

drive_service = build("drive", "v3", credentials=creds)
sheets_service = build("sheets", "v4", credentials=creds)

# ==========================
# Helper Functions
# ==========================
def upload_file(file, file_name):
    """Upload file lên Google Drive và trả về file_id"""
    file_metadata = {"name": file_name, "parents": [FOLDER_ID]}
    media = MediaFileUpload(file, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

    # Set permission cho bất kỳ ai có link
    drive_service.permissions().create(fileId=uploaded["id"], body={"type": "anyone", "role": "reader"}).execute()
    return uploaded["id"]

def append_to_sheet(data_row):
    """Thêm 1 dòng vào Google Sheets"""
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="A:F",
        valueInputOption="USER_ENTERED",
        body={"values": [data_row]}
    ).execute()

def read_sheet():
    """Đọc toàn bộ sheet"""
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="A:F").execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame(columns=["Số VB", "Tên VB", "Ngày ban hành", "Cơ quan ban hành", "Link", "FileID"])
    return pd.DataFrame(values[1:], columns=values[0])

def delete_file(file_id):
    """Xóa file trên Drive"""
    drive_service.files().delete(fileId=file_id).execute()

def update_sheet_after_delete(df):
    """Ghi đè dữ liệu mới vào Sheet sau khi xóa"""
    body = {"values": [df.columns.tolist()] + df.values.tolist()}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range="A:F",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

# ==========================
# UI Streamlit
# ==========================
st.title("📄 Quản lý Văn bản")

tab1, tab2 = st.tabs(["➕ Thêm văn bản", "📋 Danh sách & Quản lý"])

# ===== Tab 1: Upload =====
with tab1:
    so_vb = st.text_input("Số văn bản")
    ten_vb = st.text_input("Tên văn bản")
    ngay_ban_hanh = st.date_input("Ngày ban hành", format="DD/MM/YYYY")
    co_quan = st.text_input("Cơ quan ban hành")
    file_upload = st.file_uploader("Chọn file", type=["pdf", "doc", "docx", "xls", "xlsx"])

    if st.button("📤 Upload"):
        if not all([so_vb, ten_vb, ngay_ban_hanh, co_quan, file_upload]):
            st.error("⚠️ Vui lòng nhập đủ thông tin")
        else:
            # Lưu file tạm
            temp_path = f"/tmp/{file_upload.name}"
            with open(temp_path, "wb") as f:
                f.write(file_upload.getbuffer())

            # Upload lên Drive
            file_id = upload_file(temp_path, file_upload.name)
            link = f"https://drive.google.com/file/d/{file_id}/view"

            # Append vào Sheets
            append_to_sheet([
                so_vb,
                ten_vb,
                ngay_ban_hanh.strftime("%d/%m/%Y"),
                co_quan,
                link,
                file_id
            ])

            st.success("✅ Đã thêm văn bản thành công")

# ===== Tab 2: Quản lý =====
with tab2:
    df = read_sheet()

    # Bộ lọc
    keyword = st.text_input("🔍 Tìm kiếm từ khóa")
    start_date = st.date_input("Từ ngày", value=None, format="DD/MM/YYYY")
    end_date = st.date_input("Đến ngày", value=None, format="DD/MM/YYYY")

    if keyword:
        df = df[df.apply(lambda row: keyword.lower() in row.astype(str).str.lower().to_string(), axis=1)]

    if start_date:
        df = df[pd.to_datetime(df["Ngày ban hành"], format="%d/%m/%Y") >= pd.to_datetime(start_date)]
    if end_date:
        df = df[pd.to_datetime(df["Ngày ban hành"], format="%d/%m/%Y") <= pd.to_datetime(end_date)]

    st.dataframe(df, use_container_width=True)

    # Xuất Excel
    output = io.BytesIO()
    df.to_excel(output, index=False)
    st.download_button("📥 Xuất Excel", data=output.getvalue(), file_name="vanban.xlsx")

    # Xóa file
    selected_idx = st.selectbox("Chọn dòng để xóa", options=range(len(df)), format_func=lambda x: df.iloc[x, 1] if not df.empty else "")
    if st.button("🗑 Xóa"):
        if not df.empty:
            file_id_to_delete = df.iloc[selected_idx]["FileID"]
            delete_file(file_id_to_delete)

            # Xóa trong dataframe gốc (không chỉ bản lọc)
            all_df = read_sheet()
            all_df = all_df[all_df["FileID"] != file_id_to_delete]
            update_sheet_after_delete(all_df)
            st.success("✅ Đã xóa thành công")
