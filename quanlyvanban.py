import os
import io
import base64
import unicodedata
import tempfile
import pandas as pd
import streamlit as st
import base64
from urllib.parse import quote


from upload_to_dropbox import (
    upload_file_to_dropbox,
    download_bytes_from_dropbox,
    delete_file_from_dropbox,
)

# ============ CSS tinh chỉnh UI ============
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.stTextInput>div>div>input, .stMultiSelect div[data-baseweb="select"] { min-height: 42px; }
.stButton>button { padding: 0.35rem 0.7rem; border-radius: 8px; font-size: 0.9rem; }
.btn-cell .stButton>button { padding: 0.25rem 0.55rem; font-size: 0.85rem; }
.stDataFrame, .stTable { font-size: 0.92rem; }
.badge { background:#eef3ff; color:#2c3e50; padding:2px 8px; border-radius:999px; font-size:.8rem; }
hr { margin: 0.6rem 0; }
</style>
""", unsafe_allow_html=True)

# ============ Helpers ============
def _clean_path(val: str) -> str:
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()

def _norm(s: str) -> str:
    """Chuẩn hóa để tìm kiếm: bỏ dấu, lower, strip."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

def _excel_bytes_from_df(df: pd.DataFrame) -> bytes:
    """Xuất DataFrame ra XLSX (ưu tiên openpyxl; fallback xlsxwriter)."""
    buf = io.BytesIO()

    # Thử openpyxl trước (phổ biến hơn)
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
            # (openpyxl không có autofit, có thể bỏ qua)
        buf.seek(0)
        return buf.read()
    except Exception as e_openpyxl:
        pass

    # Fallback sang xlsxwriter nếu openpyxl không có
    try:
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
            ws = writer.sheets["DanhSach"]
            for i, col in enumerate(df.columns):
                width = min(40, max(12, int(df[col].astype(str).map(len).max() * 1.1)))
                ws.set_column(i, i, width)
        buf.seek(0)
        return buf.read()
    except Exception as e_xlsx:
        # Cả 2 đều không có -> gợi ý cài
        raise RuntimeError(
            "Chưa cài thư viện tạo Excel. Hãy thêm `openpyxl` (khuyên dùng) "
            "hoặc `xlsxwriter` vào requirements.txt / pip install."
        ) from e_xlsx


def _pdf_preview_safe(data: bytes, height: int = 700):
    try:
        # Cách 1: nhúng trực tiếp
        b64 = base64.b64encode(data).decode("utf-8")
        src = f"data:application/pdf;base64,{b64}"
        st.components.v1.html(
            f'<iframe src="{src}" width="100%" height="{height}" type="application/pdf"></iframe>',
            height=height + 8,
            scrolling=True,
        )
    except Exception:
        pass  # nếu lỗi sẽ thử cách 2

    # Cách 2: pdf.js + link tải
    b64 = base64.b64encode(data).decode("utf-8")
    data_url = f"data:application/pdf;base64,{b64}"
    viewer = "https://mozilla.github.io/pdf.js/web/viewer.html?file=" + quote(data_url, safe="")
    st.components.v1.iframe(viewer, height=height, scrolling=True)
    st.markdown(f"[📄 Mở PDF trong tab mới]({viewer})", unsafe_allow_html=True)
    st.download_button("⬇ Tải PDF", data=data, file_name="preview.pdf", mime="application/pdf")
# ============ Title ============
st.set_page_config(page_title="Quản lý Văn bản", layout="wide")
st.title("📚 Quản lý Văn bản - Dropbox")

# ============ Form nhập ============
with st.form("form_vanban", clear_on_submit=False):
    cL, cR = st.columns([2, 1])

    with cL:
        so_van_ban = st.text_input("Số văn bản")
        tieu_de     = st.text_input("Tiêu đề")
        co_quan     = st.text_input("Cơ quan ban hành")
        linh_vuc    = st.text_input("Lĩnh vực")

    with cR:
        st.markdown("**Đính kèm (PDF/DOCX)**")
        file_upload = st.file_uploader("", type=["pdf", "docx"])
        st.caption("💡 Kéo–thả file vào đây. Dung lượng ≤ 200MB / tệp.")

    submitted = st.form_submit_button("💾 Lưu văn bản", type="primary")

    if submitted:
        dropbox_path = None
        if file_upload:
            suffix = os.path.splitext(file_upload.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_upload.read())
                tmp_path = tmp.name
            try:
                dropbox_path = upload_file_to_dropbox(tmp_path, file_upload.name)
                st.toast("✅ Upload thành công!", icon="✅")
            except Exception as e:
                st.error(f"Lỗi upload: {e}")
            finally:
                os.remove(tmp_path)

        row = {
            "Số văn bản": so_van_ban,
            "Tiêu đề": tieu_de,
            "Cơ quan": co_quan,
            "Lĩnh vực": linh_vuc,
            "File Dropbox": dropbox_path if dropbox_path else "Không có",
        }

        if not os.path.exists("vanban.csv"):
            pd.DataFrame([row]).to_csv("vanban.csv", index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame([row]).to_csv("vanban.csv", mode="a", header=False, index=False, encoding="utf-8-sig")

        if dropbox_path:
            st.success("Văn bản đã được lưu.")
        else:
            st.warning("Đã lưu thông tin, nhưng chưa có file Dropbox.")

st.subheader("🗂️ Danh sách Văn bản đã lưu")

# ============ Đọc dữ liệu & Tìm kiếm/Lọc ============
if os.path.exists("vanban.csv"):
    df = pd.read_csv("vanban.csv", keep_default_na=False)
    if "File Dropbox" in df.columns:
        df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)

    with st.expander("🔎 Tìm kiếm & bộ lọc", expanded=True):
        q = st.text_input("Từ khóa", placeholder="Nhập số văn bản, tiêu đề, cơ quan, lĩnh vực, tên file...")

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 0.8, 1])
        sel_coquan  = c1.multiselect("Cơ quan", sorted([x for x in df.get("Cơ quan", "").unique() if str(x).strip()]))
        sel_linhvuc = c2.multiselect("Lĩnh vực", sorted([x for x in df.get("Lĩnh vực", "").unique() if str(x).strip()]))
        sel_ext     = c3.multiselect("Định dạng file", ["pdf", "docx"])
        page_size   = c4.selectbox("Mỗi trang", [10, 20, 50, 100], index=0)
        export_btn  = c5.button("⬇️ Xuất Excel (kết quả lọc)")

    # Cột chuẩn hóa tìm kiếm
    cols_join = [
        df.get("Số văn bản", "").astype(str),
        df.get("Tiêu đề", "").astype(str),
        df.get("Cơ quan", "").astype(str),
        df.get("Lĩnh vực", "").astype(str),
        df.get("File Dropbox", "").astype(str),
    ]
    df["_norm_row"] = (cols_join[0] + " " + cols_join[1] + " " + cols_join[2] + " " + cols_join[3] + " " + cols_join[4]).map(_norm)

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
    if "_norm_row" in filtered.columns:
        filtered = filtered.drop(columns=["_norm_row"])

    # Xuất Excel
    if export_btn:
        xlsx_data = _excel_bytes_from_df(filtered)
        st.download_button("⬇️ Tải Excel", data=xlsx_data, file_name="vanban_loc.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ============ Phân trang ============
    total = len(filtered)
    if total == 0:
        st.info("Không có dữ liệu phù hợp.")
    else:
        pages = (total + page_size - 1) // page_size
        pg_col1, pg_col2 = st.columns([1, 6])
        page = pg_col1.number_input("Trang", min_value=1, max_value=max(pages, 1), value=1, step=1)
        pg_col2.markdown(f"<span class='badge'>Tổng: {total} dòng • {pages} trang</span>", unsafe_allow_html=True)

        start = (page - 1) * page_size
        end   = start + page_size
        show  = filtered.iloc[start:end].reset_index(drop=True)

        # ============ Render bảng + hành động ============
        H = st.columns([0.35, 1.0, 1.8, 1.1, 1.1, 1.6, 0.7, 0.7, 0.7])
        H[0].markdown("**#**")
        H[1].markdown("**Số văn bản**")
        H[2].markdown("**Tiêu đề**")
        H[3].markdown("**Cơ quan**")
        H[4].markdown("**Lĩnh vực**")
        H[5].markdown("**File**")
        H[6].markdown("**👁 Xem**")
        H[7].markdown("**⬇️ Tải**")
        H[8].markdown("**🗑 Xóa**")

        if "preview_path" not in st.session_state:
            st.session_state.preview_path = ""

        for idx, row in show.iterrows():
            dropbox_path = _clean_path(row.get("File Dropbox", ""))
            file_name = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

            c = st.columns([0.35, 1.0, 1.8, 1.1, 1.1, 1.6, 0.7, 0.7, 0.7])
            c[0].write(f"**{start+idx+1}**")
            c[1].write(row.get("Số văn bản", ""))
            c[2].write(row.get("Tiêu đề", ""))
            c[3].write(row.get("Cơ quan", ""))
            c[4].write(row.get("Lĩnh vực", ""))
            c[5].write(file_name or "-")

            if dropbox_path and dropbox_path.startswith("/"):
                # 👁 Xem (PDF)
                with c[6].container():
                    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
                    if file_name.lower().endswith(".pdf"):
                        if st.button("👁", key=f"prev_{dropbox_path}"):
                            st.session_state.preview_path = dropbox_path
                    else:
                        st.button("—", key=f"prev_dis_{dropbox_path}", disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                # ⬇️ Tải
                with c[7].container():
                    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
                    try:
                        file_bytes = download_bytes_from_dropbox(dropbox_path)
                        st.download_button("⬇️", data=file_bytes, file_name=file_name or "file",
                                           mime="application/octet-stream", key=f"dl_{dropbox_path}")
                    except Exception:
                        st.button("⚠️", key=f"warn_{dropbox_path}", disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                # 🗑 Xóa
                with c[8].container():
                    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{dropbox_path}"):
                        try:
                            delete_file_from_dropbox(dropbox_path)
                        except Exception as e:
                            st.error(f"Lỗi xóa Dropbox: {e}")

                        full_df = pd.read_csv("vanban.csv", keep_default_na=False)
                        full_df["File Dropbox"] = full_df["File Dropbox"].apply(_clean_path)
                        full_df = full_df[full_df["File Dropbox"] != dropbox_path]
                        full_df.to_csv("vanban.csv", index=False, encoding="utf-8-sig")
                        st.success(f"Đã xóa: {file_name}")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                c[6].write("-"); c[7].write("-"); c[8].write("-")

        # ============ Khu vực xem trước PDF ============
        if st.session_state.preview_path:
            st.markdown("---")
            st.subheader("👁 Xem trước")
            try:
                pdf_bytes = download_bytes_from_dropbox(st.session_state.preview_path)
                _pdf_preview_safe(pdf_bytes, height=700)
            except Exception as e:
                st.error(f"Không xem trước được PDF: {e}")
            if st.button("Đóng xem trước"):
                st.session_state.preview_path = ""
else:
    st.info("Chưa có văn bản nào được lưu.")
