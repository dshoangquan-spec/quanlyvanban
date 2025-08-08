import streamlit as st
import pandas as pd
import tempfile
import os
from upload_to_dropbox import upload_file_to_dropbox  # trả về đường dẫn Dropbox
from upload_to_dropbox import download_bytes_from_dropbox

# Thiết lập giao diện
st.set_page_config(page_title="Quản lý Văn bản", layout="wide")
st.title("📚 Quản lý Văn bản - Dropbox")

with st.form("form_vanban"):
    so_van_ban = st.text_input("Số văn bản")
    tieu_de = st.text_input("Tiêu đề")
    co_quan = st.text_input("Cơ quan ban hành")
    linh_vuc = st.text_input("Lĩnh vực")
    file_upload = st.file_uploader("Đính kèm file (PDF, DOCX)", type=["pdf", "docx"])

    submitted = st.form_submit_button("Lưu văn bản")

    if submitted:
        dropbox_path = None

        if file_upload:
            # Lưu tạm file rồi upload
            suffix = os.path.splitext(file_upload.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_upload.read())
                tmp_path = tmp.name
            try:
                # ✅ Upload vào thư mục cố định (đặt trong upload_to_dropbox.py)
                dropbox_path = upload_file_to_dropbox(tmp_path, file_upload.name)
            except Exception as e:
                st.error(f"Lỗi upload: {e}")
            finally:
                os.remove(tmp_path)

        # Ghi vào CSV
        row = {
            "Số văn bản": so_van_ban,
            "Tiêu đề": tieu_de,
            "Cơ quan": co_quan,
            "Lĩnh vực": linh_vuc,
            "File Dropbox": dropbox_path if dropbox_path else "Không có"
        }

        if not os.path.exists("vanban.csv"):
            pd.DataFrame([row]).to_csv("vanban.csv", index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame([row]).to_csv("vanban.csv", mode="a", header=False, index=False, encoding="utf-8-sig")

        if dropbox_path:
            st.success("✅ Văn bản đã được lưu và upload lên Dropbox!")
            st.code(dropbox_path)
        else:
            st.warning("Đã lưu thông tin nhưng chưa có file Dropbox.")

# Hiển thị danh sách đã lưu + nút tải
st.subheader("📄 Danh sách Văn bản đã lưu")
if os.path.exists("vanban.csv"):
    df = pd.read_csv("vanban.csv")

    # Hiển thị bảng
    st.dataframe(df, use_container_width=True)

    st.markdown("### ⬇️ Tải file đã lưu")
    for i, row in df.iterrows():
        dropbox_path = str(row.get("File Dropbox", "")).strip()
        if not dropbox_path.startswith("/"):
            continue  # bỏ qua các hàng chưa có đường dẫn Dropbox hợp lệ

        file_name = os.path.basename(dropbox_path)
        cols = st.columns([0.5, 2, 1])
        with cols[0]:
            st.write(f"**{i+1}.**")
        with cols[1]:
            st.write(f"{file_name}")
            st.caption(dropbox_path)
        with cols[2]:
            try:
                file_bytes = download_bytes_from_dropbox(dropbox_path)
                st.download_button(
                    label="⬇️ Tải",
                    data=file_bytes,
                    file_name=file_name,
                    mime="application/octet-stream",
                    key=f"dl_{i}",
                )
            except Exception as e:
                st.error(f"Lỗi tải: {e}")
else:
    st.info("Chưa có văn bản nào được lưu.")
