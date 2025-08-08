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
def _clean_path(val: str) -> str:
    """Loại bỏ chuỗi thông báo còn sót, trả về path Dropbox chuẩn /..."""
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()

st.subheader("📄 Danh sách Văn bản đã lưu")
if os.path.exists("vanban.csv"):
    # Đọc CSV, tránh NaN
    df = pd.read_csv("vanban.csv", keep_default_na=False)
    # Chuẩn hóa cột "File Dropbox" thành path sạch
    if "File Dropbox" in df.columns:
        df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)

    # Header hàng
    h = st.columns([0.4, 1.2, 1.6, 1.2, 1.2, 1.6, 0.8, 0.8])
    h[0].markdown("**#**")
    h[1].markdown("**Số văn bản**")
    h[2].markdown("**Tiêu đề**")
    h[3].markdown("**Cơ quan**")
    h[4].markdown("**Lĩnh vực**")
    h[5].markdown("**File Dropbox**")
    h[6].markdown("**Tải**")
    h[7].markdown("**Xóa**")

    for i, row in df.iterrows():
        dropbox_path = _clean_path(row.get("File Dropbox", ""))
        file_name = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

        cols = st.columns([0.4, 1.2, 1.6, 1.2, 1.2, 1.6, 0.8, 0.8])
        cols[0].write(f"**{i+1}**")
        cols[1].write(row.get("Số văn bản", ""))
        cols[2].write(row.get("Tiêu đề", ""))
        cols[3].write(row.get("Cơ quan", ""))
        cols[4].write(row.get("Lĩnh vực", ""))
        cols[5].write(file_name if file_name else "-")

        if dropbox_path and dropbox_path.startswith("/"):
            # Nút tải
            try:
                file_bytes = download_bytes_from_dropbox(dropbox_path)
                cols[6].download_button(
                    "⬇️ Tải",
                    data=file_bytes,
                    file_name=file_name or "file",
                    mime="application/octet-stream",
                    key=f"dl_{i}",
                )
            except Exception as e:
                cols[6].warning("Không tải được")

            # Nút xóa
            if cols[7].button("🗑 Xóa", key=f"del_{i}"):
                try:
                    delete_file_from_dropbox(dropbox_path)   # Xóa trên Dropbox
                except Exception as e:
                    st.error(f"Lỗi xóa trên Dropbox: {e}")
                # Xóa khỏi CSV & reload
                df = df.drop(index=i).reset_index(drop=True)
                df.to_csv("vanban.csv", index=False, encoding="utf-8-sig")
                st.success(f"Đã xóa: {file_name}")
                st.rerun()
        else:
            cols[6].write("-")
            cols[7].write("-")
else:
    st.info("Chưa có văn bản nào được lưu.")
