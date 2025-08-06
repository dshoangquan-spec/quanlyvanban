import streamlit as st
import pandas as pd
import tempfile
import os
from upload_to_drive import upload_file_to_drive

# ID của thư mục Google Drive bạn đã chia sẻ cho Service Account
FOLDER_ID = "0B85NRfuypJmeZWRYcXY3czdXcVk"

st.set_page_config(page_title="Quản lý Văn bản", layout="wide")
st.title("📚 Quản lý Văn bản - Google Drive")

# Form nhập thông tin văn bản
with st.form("form_vanban"):
    so_van_ban = st.text_input("Số văn bản")
    tieu_de = st.text_input("Tiêu đề")
    co_quan = st.text_input("Cơ quan ban hành")
    linh_vuc = st.text_input("Lĩnh vực")
    file_upload = st.file_uploader("Đính kèm file (PDF, DOCX)", type=["pdf", "docx"])

    submitted = st.form_submit_button("Lưu văn bản")

    if submitted:
        file_url = None

        if file_upload:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_upload.read())
                tmp_path = tmp.name
                # Gọi hàm upload
                file_url = upload_file_to_drive(tmp_path, file_upload.name, FOLDER_ID)
                os.remove(tmp_path)

        # Ghi vào CSV
        row = {
            "Số văn bản": so_van_ban,
            "Tiêu đề": tieu_de,
            "Cơ quan": co_quan,
            "Lĩnh vực": linh_vuc,
            "File Google Drive": file_url if file_url else "Không có"
        }

        if not os.path.exists("vanban.csv"):
            pd.DataFrame([row]).to_csv("vanban.csv", index=False)
        else:
            pd.DataFrame([row]).to_csv("vanban.csv", mode="a", header=False, index=False)

        st.success("✅ Văn bản đã được lưu!")
        if file_url:
            st.markdown(f"🔗 [Xem file trên Google Drive]({file_url})")

# Hiển thị danh sách đã lưu
st.subheader("📄 Danh sách Văn bản đã lưu")
if os.path.exists("vanban.csv"):
    df = pd.read_csv("vanban.csv")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Chưa có văn bản nào được lưu.")
