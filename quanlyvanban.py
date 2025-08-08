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
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()

def _norm(s: str) -> str:
    """Chuẩn hóa để tìm kiếm: bỏ dấu, lower, strip."""
    s = str(s or "")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

st.subheader("📄 Danh sách Văn bản đã lưu")
if os.path.exists("vanban.csv"):
    # Đọc CSV an toàn, không sinh NaN
    df = pd.read_csv("vanban.csv", keep_default_na=False)

    # Chuẩn hóa cột đường dẫn
    if "File Dropbox" in df.columns:
        df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)

    # ---------- Khu vực TÌM KIẾM & BỘ LỌC ----------
    st.markdown("### 🔎 Tìm kiếm & bộ lọc")

    # Hàng 1: ô từ khóa
    q = st.text_input("Từ khóa", placeholder="Nhập số văn bản, tiêu đề, cơ quan, lĩnh vực, tên file...")

    # Hàng 2: filter theo danh mục
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    sel_coquan  = c1.multiselect("Cơ quan", sorted([x for x in df.get("Cơ quan", "").unique() if str(x).strip()]))
    sel_linhvuc = c2.multiselect("Lĩnh vực", sorted([x for x in df.get("Lĩnh vực", "").unique() if str(x).strip()]))

    # Lọc theo đuôi file (pdf/docx)
    all_ext = ["pdf", "docx"]
    sel_ext = c3.multiselect("Định dạng file", all_ext)

    # Nút xóa/clear filter
    if c4.button("🔄 Xóa bộ lọc"):
        st.experimental_rerun()

    # Tạo cột tổng hợp để tìm kiếm toàn văn
    cols_to_join = [df.get("Số văn bản", ""), df.get("Tiêu đề", ""), df.get("Cơ quan", ""),
                    df.get("Lĩnh vực", ""), df.get("File Dropbox", "")]
    df["_norm_row"] = (cols_to_join[0].astype(str) + " " +
                       cols_to_join[1].astype(str) + " " +
                       cols_to_join[2].astype(str) + " " +
                       cols_to_join[3].astype(str) + " " +
                       cols_to_join[4].astype(str)).map(_norm)

    # Áp dụng tìm kiếm + lọc
    filtered = df.copy()

    if q:
        nq = _norm(q)
        filtered = filtered[filtered["_norm_row"].str.contains(nq, na=False)]

    if sel_coquan:
        filtered = filtered[filtered.get("Cơ quan", "").isin(sel_coquan)]

    if sel_linhvuc:
        filtered = filtered[filtered.get("Lĩnh vực", "").isin(sel_linhvuc)]

    if sel_ext:
        filtered = filtered[filtered["File Dropbox"].str.lower().str.endswith(tuple(sel_ext))]

    # Bỏ cột phụ
    if "_norm_row" in filtered.columns:
        filtered = filtered.drop(columns=["_norm_row"])

    # ---------- BẢNG + nút Tải / Xóa trên cùng một hàng ----------
    # Header
    h = st.columns([0.4, 1.1, 1.8, 1.2, 1.2, 1.8, 0.8, 0.8])
    h[0].markdown("**#**")
    h[1].markdown("**Số văn bản**")
    h[2].markdown("**Tiêu đề**")
    h[3].markdown("**Cơ quan**")
    h[4].markdown("**Lĩnh vực**")
    h[5].markdown("**File Dropbox**")
    h[6].markdown("**Tải**")
    h[7].markdown("**Xóa**")

    for idx, row in filtered.reset_index(drop=True).iterrows():
        dropbox_path = _clean_path(row.get("File Dropbox", ""))
        file_name = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

        cols = st.columns([0.4, 1.1, 1.8, 1.2, 1.2, 1.8, 0.8, 0.8])
        cols[0].write(f"**{idx+1}**")
        cols[1].write(row.get("Số văn bản", ""))
        cols[2].write(row.get("Tiêu đề", ""))
        cols[3].write(row.get("Cơ quan", ""))
        cols[4].write(row.get("Lĩnh vực", ""))
        cols[5].write(file_name or "-")

        if dropbox_path and dropbox_path.startswith("/"):
            # Nút tải
            try:
                file_bytes = download_bytes_from_dropbox(dropbox_path)
                cols[6].download_button(
                    label="⬇️ Tải",
                    data=file_bytes,
                    file_name=file_name or "file",
                    mime="application/octet-stream",
                    key=f"dl_{dropbox_path}",
                )
            except Exception:
                cols[6].warning("Không tải được")

            # Nút xóa
            if cols[7].button("🗑 Xóa", key=f"del_{dropbox_path}"):
                try:
                    delete_file_from_dropbox(dropbox_path)   # Xóa Dropbox
                except Exception as e:
                    st.error(f"Lỗi xóa trên Dropbox: {e}")
                # Xóa khỏi CSV theo đúng chỉ mục gốc trong file
                # -> dùng mask để tìm hàng khớp path
                full_df = pd.read_csv("vanban.csv", keep_default_na=False)
                full_df["File Dropbox"] = full_df["File Dropbox"].apply(_clean_path)
                full_df = full_df[full_df["File Dropbox"] != dropbox_path]
                full_df.to_csv("vanban.csv", index=False, encoding="utf-8-sig")
                st.success(f"Đã xóa: {file_name}")
                st.rerun()
        else:
            cols[6].write("-")
            cols[7].write("-")
else:
    st.info("Chưa có văn bản nào được lưu.")
