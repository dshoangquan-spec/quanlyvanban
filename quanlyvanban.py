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

# Hiển thị danh sách đã lưu
st.subheader("📄 Danh sách Văn bản đã lưu")
if os.path.exists("vanban.csv"):
    df = pd.read_csv("vanban.csv")

    # Duyệt từng dòng
    for i, row in df.iterrows():
        st.markdown("---")
        cols = st.columns([0.3, 1.2, 1.2, 1, 1.2, 0.8, 0.8])

        cols[0].write(f"**{i+1}**")  # Số thứ tự
        cols[1].write(row.get("Số văn bản", ""))
        cols[2].write(row.get("Tiêu đề", ""))
        cols[3].write(row.get("Cơ quan", ""))
        cols[4].write(row.get("Lĩnh vực", ""))

        dropbox_path = str(row.get("File Dropbox", "")).strip()
        file_name = os.path.basename(dropbox_path) if dropbox_path else ""

        # Nút tải file
        if dropbox_path and dropbox_path.startswith("/"):
            try:
                file_bytes = download_bytes_from_dropbox(dropbox_path)
                cols[5].download_button(
                    label="⬇️ Tải",
                    data=file_bytes,
                    file_name=file_name,
                    mime="application/octet-stream",
                    key=f"dl_{i}"
                )
            except Exception as e:
                cols[5].error("Lỗi tải")

            # Nút xóa file
            if cols[6].button("🗑 Xóa", key=f"del_{i}"):
                try:
                    dbx.files_delete_v2(dropbox_path)
                    df.drop(index=i, inplace=True)
                    df.to_csv("vanban.csv", index=False)
                    st.success(f"Đã xóa: {file_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi xóa: {e}")
        else:
            cols[5].write("-")
            cols[6].write("-")
else:
    st.info("Chưa có văn bản nào được lưu.")
