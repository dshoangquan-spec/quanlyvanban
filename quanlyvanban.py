# quanlyvanban.py
import os
import io
import unicodedata
import tempfile
import pandas as pd
import streamlit as st
from datetime import date

from upload_to_dropbox import (
    upload_file_to_dropbox,
    download_bytes_from_dropbox,
    delete_file_from_dropbox,
)

# =========================
# Cấu hình trang + CSS
# =========================
st.set_page_config(page_title="Quản lý Văn bản", layout="wide")
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

st.title("📚 Quản lý Văn bản - Dropbox")

DATA_FILE = "vanban.csv"

# =========================
# Helpers
# =========================
def _clean_path(val: str) -> str:
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()

def _norm(s: str) -> str:
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

def _format_ddmmyyyy(dt) -> str:
    """Nhận Timestamp/str/date -> trả về dd/mm/yyyy hoặc chuỗi gốc."""
    if pd.isna(dt):
        return ""
    try:
        return pd.to_datetime(dt, errors="coerce").strftime("%d/%m/%Y")
    except Exception:
        return str(dt)

def _export_table_bytes(df: pd.DataFrame):
    """Xuất Excel (ưu tiên openpyxl -> xlsxwriter -> CSV)."""
    # 1) openpyxl
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
        buf.seek(0)
        return (
            buf.read(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "vanban_loc.xlsx",
        )
    except Exception:
        pass
    # 2) xlsxwriter
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="DanhSach")
            ws = writer.sheets["DanhSach"]
            for i, col in enumerate(df.columns):
                width = min(40, max(12, int(df[col].astype(str).map(len).max() * 1.1)))
                ws.set_column(i, i, width)
        buf.seek(0)
        return (
            buf.read(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "vanban_loc.xlsx",
        )
    except Exception:
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        return csv_bytes, "text/csv", "vanban_loc.csv"

# =========================
# Form nhập liệu + upload
# =========================
with st.form("form_vanban", clear_on_submit=False):
    cL, cR = st.columns([2, 1])

    with cL:
        so_van_ban  = st.text_input("Số văn bản")
        tieu_de     = st.text_input("Tiêu đề")
        co_quan     = st.text_input("Cơ quan ban hành")
        linh_vuc    = st.text_input("Lĩnh vực")
        # Hiển thị theo VN
        ngay_bh     = st.date_input("Ngày ban hành", value=date.today(), format="DD/MM/YYYY")

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

        # Lưu **cả hai cột**:
        # - NgayBH (ISO, dùng để lọc & tính toán)
        # - Ngày ban hành (dd/mm/yyyy) để hiển thị/Excel
        ngay_bh_iso = ngay_bh.isoformat()
        ngay_bh_vn  = ngay_bh.strftime("%d/%m/%Y")

        row = {
            "Số văn bản": so_van_ban,
            "Tiêu đề": tieu_de,
            "Cơ quan": co_quan,
            "Lĩnh vực": linh_vuc,
            "NgayBH": ngay_bh_iso,
            "Ngày ban hành": ngay_bh_vn,
            "File Dropbox": dropbox_path if dropbox_path else "Không có",
        }

        if not os.path.exists(DATA_FILE):
            pd.DataFrame([row]).to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame([row]).to_csv(DATA_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")

        if dropbox_path:
            st.success("Văn bản đã được lưu.")
        else:
            st.warning("Đã lưu thông tin, nhưng chưa có file Dropbox.")

st.subheader("🗂️ Danh sách Văn bản đã lưu")

# =========================
# Đọc dữ liệu & tìm kiếm / lọc
# =========================
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, keep_default_na=False)

    # Chuẩn hóa cột file
    if "File Dropbox" in df.columns:
        df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)

    # Chuẩn hóa cột ngày:
    # - NgayBH là ISO (YYYY-MM-DD); nếu thiếu, sinh từ "Ngày ban hành" (VN)
    if "NgayBH" not in df.columns:
        # fallback nếu các bản cũ chưa có cột NgayBH
        df["NgayBH"] = pd.to_datetime(
            df.get("Ngày ban hành", ""), errors="coerce", dayfirst=True
        ).dt.strftime("%Y-%m-%d").fillna("")
    # Series datetime để lọc
    NgayBH_dt = pd.to_datetime(df["NgayBH"], errors="coerce")

    with st.expander("🔎 Tìm kiếm & bộ lọc", expanded=True):
        q = st.text_input("Từ khóa", placeholder="Nhập số văn bản, tiêu đề, cơ quan, lĩnh vực, tên file...")

        c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1.2, 0.9, 1.1])
        sel_coquan  = c1.multiselect("Cơ quan", sorted([x for x in df.get("Cơ quan", "").unique() if str(x).strip()]))
        sel_linhvuc = c2.multiselect("Lĩnh vực", sorted([x for x in df.get("Lĩnh vực", "").unique() if str(x).strip()]))
        sel_ext     = c3.multiselect("Định dạng file", ["pdf", "docx"])

        # min/max ngày có thực (dựa trên NgayBH_dt)
        dt_series = NgayBH_dt.dropna()
        if len(dt_series) == 0:
            dt_min = date.today()
            dt_max = date.today()
        else:
            dt_min = dt_series.min().date()
            dt_max = dt_series.max().date()

        # Bộ lọc khoảng ngày ban hành (hiển thị VN)
        date_from, date_to = c4.date_input(
            "Từ / Đến (ngày BH)",
            value=(dt_min, dt_max),
            format="DD/MM/YYYY"
        )
        page_size   = c5.selectbox("Mỗi trang", [10, 20, 50, 100], index=0)
        export_btn  = c6.button("⬇️ Xuất Excel/CSV (kết quả lọc)")

    # Cột chuẩn hóa tìm kiếm (gộp các trường; dùng NgayBH ISO cho ổn)
    cols_join = [
        df.get("Số văn bản", "").astype(str),
        df.get("Tiêu đề", "").astype(str),
        df.get("Cơ quan", "").astype(str),
        df.get("Lĩnh vực", "").astype(str),
        df.get("File Dropbox", "").astype(str),
        NgayBH_dt.dt.strftime("%Y-%m-%d").fillna(""),  # chuẩn tìm kiếm
    ]
    df["_norm_row"] = (
        cols_join[0] + " " + cols_join[1] + " " + cols_join[2] + " " +
        cols_join[3] + " " + cols_join[4] + " " + cols_join[5]
    ).map(_norm)

    # Lọc theo từ khóa/các field
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

    # Lọc theo khoảng ngày ban hành (dựa vào NgayBH_dt)
    if isinstance(date_from, date) and isinstance(date_to, date):
        series_date = pd.to_datetime(filtered["NgayBH"], errors="coerce").dt.date
        mask_date = (series_date >= date_from) & (series_date <= date_to)
        filtered = filtered[mask_date]

    if "_norm_row" in filtered.columns:
        filtered = filtered.drop(columns=["_norm_row"])

    # Xuất Excel/CSV (đảm bảo cột hiển thị là dd/mm/yyyy)
    if export_btn:
        tmp = filtered.copy()
        # Chuẩn 'Ngày ban hành' cho đẹp
        if "Ngày ban hành" in tmp.columns:
            tmp["Ngày ban hành"] = tmp["Ngày ban hành"].apply(_format_ddmmyyyy)
        else:
            # nếu chưa có thì sinh từ NgayBH
            tmp["Ngày ban hành"] = pd.to_datetime(tmp["NgayBH"], errors="coerce").dt.strftime("%d/%m/%Y")
        data_bytes, mime, fname = _export_table_bytes(tmp.drop(columns=["NgayBH"], errors="ignore"))
        st.download_button("⬇️ Tải dữ liệu đã lọc", data=data_bytes, file_name=fname, mime=mime)

    # =========================
    # Phân trang + hiển thị
    # =========================
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

        # Hiển thị ngày kiểu VN
        show_disp = show.copy()
        if "Ngày ban hành" in show_disp.columns and show_disp["Ngày ban hành"].notna().any():
            show_disp["Ngày ban hành"] = show_disp["Ngày ban hành"].apply(_format_ddmmyyyy)
        else:
            show_disp["Ngày ban hành"] = pd.to_datetime(show_disp["NgayBH"], errors="coerce").dt.strftime("%d/%m/%Y")

        # Header
        H = st.columns([0.35, 0.9, 1.8, 1.1, 1.1, 1.1, 1.6, 0.7, 0.7])
        H[0].markdown("**#**")
        H[1].markdown("**Số văn bản**")
        H[2].markdown("**Tiêu đề**")
        H[3].markdown("**Cơ quan**")
        H[4].markdown("**Lĩnh vực**")
        H[5].markdown("**Ngày BH**")
        H[6].markdown("**File**")
        H[7].markdown("**⬇️ Tải**")
        H[8].markdown("**🗑 Xóa**")

        # Render từng hàng
        for idx, row in show_disp.iterrows():
            dropbox_path = _clean_path(row.get("File Dropbox", ""))
            file_name = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

            c = st.columns([0.35, 0.9, 1.8, 1.1, 1.1, 1.1, 1.6, 0.7, 0.7])
            c[0].write(f"**{start + idx + 1}**")
            c[1].write(row.get("Số văn bản", ""))
            c[2].write(row.get("Tiêu đề", ""))
            c[3].write(row.get("Cơ quan", ""))
            c[4].write(row.get("Lĩnh vực", ""))
            c[5].write(row.get("Ngày ban hành", ""))  # dd/mm/yyyy
            c[6].write(os.path.basename(dropbox_path) or "-")

            if dropbox_path and dropbox_path.startswith("/"):
                # ⬇️ Tải
                with c[7].container():
                    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
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
                    st.markdown("</div>", unsafe_allow_html=True)

                # 🗑 Xóa
                with c[8].container():
                    st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{start}_{idx}"):
                        try:
                            delete_file_from_dropbox(dropbox_path)
                        except Exception as e:
                            st.error(f"Lỗi xóa Dropbox: {e}")

                        full_df = pd.read_csv(DATA_FILE, keep_default_na=False)
                        full_df["File Dropbox"] = full_df["File Dropbox"].apply(_clean_path)
                        full_df = full_df[full_df["File Dropbox"] != dropbox_path]
                        full_df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
                        st.success(f"Đã xóa: {file_name}")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                c[7].write("-")
                c[8].write("-")
else:
    st.info("Chưa có văn bản nào được lưu.")
