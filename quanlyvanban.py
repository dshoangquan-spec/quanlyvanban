# -*- coding: utf-8 -*-
import os
import io
import unicodedata
import tempfile
from datetime import date, datetime

import pandas as pd
import streamlit as st

from upload_to_dropbox import (
    upload_file_to_dropbox,
    download_bytes_from_dropbox,
    delete_file_from_dropbox,
)

# ==========================
# UI Tuning
# ==========================
st.set_page_config(page_title="Quản lý Văn bản", layout="wide")
st.markdown(
    """
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.stTextInput>div>div>input, .stMultiSelect div[data-baseweb="select"] { min-height: 42px; }
.stButton>button { padding: 0.38rem 0.75rem; border-radius: 8px; font-size: 0.9rem; }
.btn-cell .stButton>button { padding: 0.30rem 0.55rem; font-size: 0.86rem; }
.badge { background:#eef3ff; color:#2c3e50; padding:2px 8px; border-radius:999px; font-size:.8rem; }
hr { margin: .75rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "vanban.csv"  # nơi lưu dữ liệu

# ==========================
# Helpers
# ==========================
def _norm(s: str) -> str:
    """Chuẩn hóa để tìm kiếm: bỏ dấu, lower, strip."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()


def _excel_bytes_from_df(df: pd.DataFrame) -> bytes:
    """Xuất DataFrame ra XLSX (ưu tiên openpyxl; fallback xlsxwriter)."""
    buf = io.BytesIO()
    # Thử openpyxl
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
        buf.seek(0)
        return buf.read()
    except Exception:
        pass
    # Fallback xlsxwriter
    try:
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
            ws = writer.sheets["DanhSach"]
            for i, col in enumerate(df.columns):
                width = min(40, max(12, int(df[col].astype(str).map(len).max() * 1.1)))
                ws.set_column(i, i, width)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        raise RuntimeError(
            "Chưa cài thư viện tạo Excel. Hãy thêm `openpyxl` (khuyên dùng) "
            "hoặc `xlsxwriter` vào môi trường."
        ) from e


def _ensure_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa cột & chuyển đổi ngày:
    - Đảm bảo tồn tại cột 'NgayBH' (ISO) để lọc/sắp xếp.
    - 'Ngày ban hành' hiển thị dạng dd/mm/yyyy.
    """
    for col in ["Số văn bản", "Tiêu đề", "Cơ quan", "Lĩnh vực", "Ngày ban hành", "NgayBH", "File Dropbox"]:
        if col not in df.columns:
            df[col] = ""

    # Nếu 'NgayBH' trống nhưng 'Ngày ban hành' đang dạng dd/mm/yyyy -> tạo ISO
    def _to_iso_from_vn(s):
        if not s:
            return ""
        s = str(s).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                d = datetime.strptime(s, fmt).date()
                return d.strftime("%Y-%m-%d")
            except Exception:
                pass
        return ""

    if (df["NgayBH"] == "").any():
        df["NgayBH"] = df["NgayBH"].fillna("")
        need_fill = df["NgayBH"] == ""
        if "Ngày ban hành" in df.columns:
            df.loc[need_fill, "NgayBH"] = df.loc[need_fill, "Ngày ban hành"].apply(_to_iso_from_vn)

    # Chuẩn hóa 'Ngày ban hành' luôn là dd/mm/yyyy (nếu có ISO)
    def _vn_from_iso(iso_str):
        iso_str = (iso_str or "").strip()
        if not iso_str:
            return ""
        try:
            d = datetime.strptime(iso_str, "%Y-%m-%d").date()
            return d.strftime("%d/%m/%Y")
        except Exception:
            # Nếu đã là dd/mm/yyyy thì giữ nguyên
            try:
                datetime.strptime(iso_str, "%d/%m/%Y")
                return iso_str
            except Exception:
                return ""

    df["Ngày ban hành"] = df["NgayBH"].apply(_vn_from_iso)
    return df


def _clean_path(val: str) -> str:
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()


# ==========================
# Title
# ==========================
st.title("📚 Quản lý Văn bản - Dropbox")

# ==========================
# Form nhập liệu
# ==========================
with st.form("form_vanban", clear_on_submit=False):
    cL, cR = st.columns([2, 1])

    with cL:
        so_van_ban = st.text_input("Số văn bản")
        tieu_de = st.text_input("Tiêu đề")
        co_quan = st.text_input("Cơ quan ban hành")
        linh_vuc = st.text_input("Lĩnh vực")
        ngay_bh = st.date_input("Ngày ban hành", value=date.today())  # chọn ngày kiểu date

    with cR:
        st.markdown("**Đính kèm (PDF/DOCX)**")
        file_upload = st.file_uploader("", type=["pdf", "docx"])
        st.caption("💡 Kéo–thả file vào đây. Dung lượng ≤ 200MB / tệp.")

    submitted = st.form_submit_button("💾 Lưu văn bản", type="primary")

    if submitted:
        dropbox_path = None
        if file_upload is not None:
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

        # Ngày ban hành hiển thị (VN) & ISO để lọc
        ngay_iso = ngay_bh.strftime("%Y-%m-%d")
        ngay_vn = ngay_bh.strftime("%d/%m/%Y")

        row = {
            "Số văn bản": so_van_ban,
            "Tiêu đề": tieu_de,
            "Cơ quan": co_quan,
            "Lĩnh vực": linh_vuc,
            "Ngày ban hành": ngay_vn,  # hiển thị
            "NgayBH": ngay_iso,        # ISO để lọc
            "File Dropbox": dropbox_path if dropbox_path else "Không có",
        }

        if not os.path.exists(DATA_FILE):
            pd.DataFrame([row]).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame([row]).to_csv(
                DATA_FILE, mode="a", header=False, index=False, encoding="utf-8-sig"
            )

        if dropbox_path:
            st.success("Văn bản đã được lưu.")
        else:
            st.warning("Đã lưu thông tin, nhưng chưa có file Dropbox.")

st.subheader("🗂️ Danh sách Văn bản đã lưu")

# ==========================
# Đọc dữ liệu & Bộ lọc
# ==========================
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, keep_default_na=False)
    df = _ensure_df_columns(df)
    df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)

    with st.expander("🔎 Tìm kiếm & bộ lọc", expanded=True):
        q = st.text_input("Từ khóa", placeholder="Nhập số VB, tiêu đề, cơ quan, lĩnh vực, tên file...")

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.1, 0.6])
        sel_coquan = c1.multiselect(
            "Cơ quan", sorted([x for x in df.get("Cơ quan", "").unique() if str(x).strip()])
        )
        sel_linhvuc = c2.multiselect(
            "Lĩnh vực", sorted([x for x in df.get("Lĩnh vực", "").unique() if str(x).strip()])
        )
        sel_ext = c3.multiselect("Định dạng file", ["pdf", "docx"])

        # Khoảng thời gian theo NgayBH (ISO), input hiển thị ngày VN
        # Lấy min/max từ dữ liệu
        try:
            df_date = pd.to_datetime(df["NgayBH"], errors="coerce").dt.date
            min_d = df_date.min() or date.today()
            max_d = df_date.max() or date.today()
        except Exception:
            min_d = max_d = date.today()

        date_from, date_to = c4.date_input(
            "Từ / Đến (ngày BH)", value=(min_d, max_d)
        )

        page_size = c5.selectbox("Mỗi trang", [10, 20, 50, 100], index=0)
        export_btn = st.button("⬇️ Xuất Excel (kết quả lọc)")

    # Cột chuẩn hóa để tìm kiếm full-text
    cols_join = [
        df.get("Số văn bản", "").astype(str),
        df.get("Tiêu đề", "").astype(str),
        df.get("Cơ quan", "").astype(str),
        df.get("Lĩnh vực", "").astype(str),
        df.get("File Dropbox", "").astype(str),
    ]
    df["_norm_row"] = (cols_join[0] + " " + cols_join[1] + " " + cols_join[2] + " " + cols_join[3] + " " + cols_join[4]).map(_norm)

    # Lọc
    filtered = df.copy()
    if q:
        nq = _norm(q)
        filtered = filtered[filtered["_norm_row"].str.contains(nq, na=False)]
    if sel_coquan:
        filtered = filtered[filtered["Cơ quan"].isin(sel_coquan)]
    if sel_linhvuc:
        filtered = filtered[filtered["Lĩnh vực"].isin(sel_linhvuc)]
    if sel_ext:
        filtered = filtered[filtered["File Dropbox"].str.lower().str.endswith(tuple(sel_ext))]
    # Lọc theo khoảng ngày
    if isinstance(date_from, date) and isinstance(date_to, date):
        mask_date = pd.to_datetime(filtered["NgayBH"], errors="coerce").dt.date
        filtered = filtered[(mask_date >= date_from) & (mask_date <= date_to)]

    if "_norm_row" in filtered.columns:
        filtered = filtered.drop(columns=["_norm_row"])

    # Xuất Excel
    if export_btn:
        export_df = filtered.drop(columns=["NgayBH"], errors="ignore")
        xlsx_data = _excel_bytes_from_df(export_df)
        st.download_button(
            "⬇️ Tải Excel",
            data=xlsx_data,
            file_name="vanban_loc.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ==========================
    # Phân trang + danh sách
    # ==========================
    total = len(filtered)
    if total == 0:
        st.info("Không có dữ liệu phù hợp.")
    else:
        pages = (total + page_size - 1) // page_size
        pg_col1, pg_col2 = st.columns([1, 6])
        page = pg_col1.number_input("Trang", min_value=1, max_value=max(pages, 1), value=1, step=1)
        pg_col2.markdown(
            f"<span class='badge'>Tổng: {total} dòng • {pages} trang</span>",
            unsafe_allow_html=True,
        )

        start = (page - 1) * page_size
        end = start + page_size
        show = filtered.iloc[start:end].reset_index(drop=True)

        H = st.columns([0.35, 1.0, 1.8, 1.1, 1.1, 1.0, 1.6, 0.8, 0.8])
        H[0].markdown("**#**")
        H[1].markdown("**Số VB**")
        H[2].markdown("**Tiêu đề**")
        H[3].markdown("**Cơ quan**")
        H[4].markdown("**Lĩnh vực**")
        H[5].markdown("**Ngày BH**")
        H[6].markdown("**File**")
        H[7].markdown("**⬇️ Tải**")
        H[8].markdown("**🗑 Xóa**")

        for idx, row in show.iterrows():
            dropbox_path = _clean_path(row.get("File Dropbox", ""))
            file_name = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

            c = st.columns([0.35, 1.0, 1.8, 1.1, 1.1, 1.0, 1.6, 0.8, 0.8])
            c[0].write(f"**{start + idx + 1}**")
            c[1].write(row.get("Số văn bản", ""))
            c[2].write(row.get("Tiêu đề", ""))
            c[3].write(row.get("Cơ quan", ""))
            c[4].write(row.get("Lĩnh vực", ""))
            c[5].write(row.get("Ngày ban hành", ""))  # dd/mm/yyyy
            c[6].write(file_name or "-")

            # Tải
with c[7].container():
    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
    if dropbox_path and dropbox_path.startswith("/"):
        try:
            file_bytes = download_bytes_from_dropbox(dropbox_path)
            st.download_button(
                "⬇️",
                data=file_bytes,
                file_name=file_name or "file",
                mime="application/octet-stream",
                key=f"dl_{start}_{idx}",
            )
        except Exception:
            st.button("⚠️", key=f"warn_{start}_{idx}", disabled=True)
    else:
        st.button("—", key=f"dl_dis_{start}_{idx}", disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Xóa
with c[8].container():
    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
    if dropbox_path and st.button("🗑", key=f"del_{start}_{idx}"):
        try:
            delete_file_from_dropbox(dropbox_path)
        except Exception as e:
            st.error(f"Lỗi xóa Dropbox: {e}")

        # Xóa khỏi CSV và reload
        all_df = pd.read_csv(DATA_FILE, keep_default_na=False)
        # Chuẩn hóa đường dẫn để so sánh
        all_df["File Dropbox"] = all_df["File Dropbox"].astype(str)
        all_df = all_df[all_df["File Dropbox"].apply(lambda x: x.strip()) != dropbox_path.strip()]
        all_df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

        st.success(f"Đã xóa: {file_name}")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
