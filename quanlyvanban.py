# quanlyvanban.py
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

# ================= UI & CSS =================
st.set_page_config(page_title="Quản lý Văn bản", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 0.8rem; padding-bottom: 2rem;}
.stTextInput>div>div>input, .stMultiSelect div[data-baseweb="select"], .stDateInput input { min-height: 42px; }
.stButton>button { padding: 0.38rem 0.9rem; border-radius: 8px; font-size: 0.92rem; }
.btn-cell .stButton>button { padding: 0.25rem 0.55rem; font-size: 0.85rem; }
.badge { background:#eef3ff; color:#2c3e50; padding:2px 8px; border-radius:999px; font-size:.8rem; }
hr { margin: 0.6rem 0; }
</style>
""", unsafe_allow_html=True)

st.title("📚 Quản lý Văn bản - Dropbox")

CSV_FILE = "vanban.csv"

# ================= Helpers =================
def _clean_path(val: str) -> str:
    """Loại bỏ tiền tố hiển thị nếu tồn tại."""
    if not isinstance(val, str):
        return ""
    return val.replace("✅ Đã upload thành công tới:", "").strip()

def _norm(s: str) -> str:
    """Chuẩn hoá tiếng Việt để tìm kiếm: bỏ dấu, to lower, trim."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

def _excel_bytes_from_df(df: pd.DataFrame) -> bytes:
    """Xuất DataFrame -> XLSX, ưu tiên openpyxl; fallback xlsxwriter."""
    buf = io.BytesIO()
    # openpyxl
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="DanhSach")
        buf.seek(0)
        return buf.read()
    except Exception:
        pass
    # xlsxwriter
    try:
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.to_excel(w, index=False, sheet_name="DanhSach")
            ws = w.sheets["DanhSach"]
            for i, col in enumerate(df.columns):
                width = min(40, max(12, int(df[col].astype(str).map(len).max() * 1.1)))
                ws.set_column(i, i, width)
        buf.seek(0)
        return buf.read()
    except Exception as e_xlsx:
        raise RuntimeError(
            "Chưa cài thư viện tạo Excel. Hãy thêm `openpyxl` (khuyên dùng) "
            "hoặc `xlsxwriter` vào requirements.txt / pip install."
        ) from e_xlsx

def _read_csv() -> pd.DataFrame:
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=[
            "Số văn bản", "Tiêu đề", "Cơ quan", "Lĩnh vực", "Ngày ban hành", "File Dropbox"
        ])
    df = pd.read_csv(CSV_FILE, keep_default_na=False)
    # bảo đảm đủ cột
    for c in ["Số văn bản", "Tiêu đề", "Cơ quan", "Lĩnh vực", "Ngày ban hành", "File Dropbox"]:
        if c not in df.columns:
            df[c] = ""
    df["File Dropbox"] = df["File Dropbox"].apply(_clean_path)
    return df

def _write_row(row: dict):
    if not os.path.exists(CSV_FILE):
        pd.DataFrame([row]).to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame([row]).to_csv(CSV_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")

# ================= Form nhập =================
with st.form("form_vanban", clear_on_submit=False):
    cL, cR = st.columns([2, 1])

    with cL:
        so_van_ban = st.text_input("Số văn bản")
        tieu_de     = st.text_input("Tiêu đề")
        co_quan     = st.text_input("Cơ quan ban hành")
        linh_vuc    = st.text_input("Lĩnh vực")
        ngay_bh     = st.date_input("Ngày ban hành", value=date.today(), format="DD/MM/YYYY")

    with cR:
        st.markdown("**Đính kèm (PDF/DOCX)**")
        file_upload = st.file_uploader("", type=["pdf", "docx"])
        st.caption("💡 Kéo–thả file vào đây. Dung lượng ≤ 200MB / tệp.")

    submitted = st.form_submit_button("💾 Lưu văn bản", type="primary")

    if submitted:
        dropbox_path = ""
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

        # Lưu ngày theo định dạng Việt Nam dd/mm/yyyy
        ngay_bh_str = ngay_bh.strftime("%d/%m/%Y")

        row = {
            "Số văn bản"   : so_van_ban.strip(),
            "Tiêu đề"      : tieu_de.strip(),
            "Cơ quan"      : co_quan.strip(),
            "Lĩnh vực"     : linh_vuc.strip(),
            "Ngày ban hành": ngay_bh_str,
            "File Dropbox" : dropbox_path if dropbox_path else "Không có",
        }
        _write_row(row)

        if dropbox_path:
            st.success("✅ Văn bản đã được lưu.")
        else:
            st.warning("Đã lưu thông tin, nhưng chưa có file Dropbox.")

# ================= Danh sách & Tìm kiếm =================
st.subheader("🗂️ Danh sách Văn bản đã lưu")
df = _read_csv()

if len(df) == 0:
    st.info("Chưa có văn bản nào được lưu.")
    st.stop()

# Chuyển cột ngày sang datetime để lọc (dayfirst=True vì dd/mm/yyyy)
df["_ngay_dt"] = pd.to_datetime(df["Ngày ban hành"], format="%d/%m/%Y", errors="coerce", dayfirst=True)

with st.expander("🔎 Tìm kiếm & bộ lọc", expanded=True):
    q = st.text_input("Từ khóa", placeholder="Nhập số văn bản, tiêu đề, cơ quan, lĩnh vực, tên file...")

    c1, c2, c3, c4, c5 = st.columns([1.1, 1.1, 1.1, 1.4, 0.8])
    sel_coquan  = c1.multiselect("Cơ quan", sorted([x for x in df["Cơ quan"].unique() if str(x).strip()]))
    sel_linhvuc = c2.multiselect("Lĩnh vực", sorted([x for x in df["Lĩnh vực"].unique() if str(x).strip()]))
    sel_ext     = c3.multiselect("Định dạng file", ["pdf", "docx"])

    # Khoảng ngày ban hành (dd/mm/yyyy)
    min_date = pd.to_datetime(df["_ngay_dt"]).min()
    max_date = pd.to_datetime(df["_ngay_dt"]).max()
    if pd.isna(min_date) or pd.isna(max_date):
        min_date, max_date = date.today(), date.today()

    start_end = c4.date_input("Từ / Đến (ngày BH)", value=(min_date.date(), max_date.date()), format="DD/MM/YYYY")
    page_size = c5.selectbox("Mỗi trang", [10, 20, 50, 100], index=0)

    export_btn = st.button("⬇️ Xuất Excel (kết quả lọc)")

# Tạo cột bình thường hóa cho tìm kiếm nhanh
cols_join = [
    df["Số văn bản"].astype(str),
    df["Tiêu đề"].astype(str),
    df["Cơ quan"].astype(str),
    df["Lĩnh vực"].astype(str),
    df["File Dropbox"].astype(str),
]
df["_norm_row"] = (cols_join[0] + " " + cols_join[1] + " " + cols_join[2] + " " + cols_join[3] + " " + cols_join[4]).map(_norm)

# Áp filter
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

# Lọc ngày: start_end là tuple 2 ngày
if isinstance(start_end, (list, tuple)) and len(start_end) == 2:
    start_date, end_date = start_end
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date,   datetime.max.time())
    filtered = filtered[(filtered["_ngay_dt"] >= pd.Timestamp(start_dt)) & (filtered["_ngay_dt"] <= pd.Timestamp(end_dt))]

# Bỏ cột nội bộ
filtered = filtered.drop(columns=[c for c in ["_norm_row", "_ngay_dt"] if c in filtered.columns])

# Xuất Excel theo kết quả lọc
if export_btn:
    xlsx_data = _excel_bytes_from_df(filtered)
    st.download_button("⬇️ Tải Excel", data=xlsx_data, file_name="vanban_loc.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============== Phân trang & Render bảng có nút tải/xóa ===============
total = len(filtered)
if total == 0:
    st.info("Không có dữ liệu phù hợp.")
    st.stop()

pages = (total + page_size - 1) // page_size
pg_col1, pg_col2 = st.columns([1, 6])
page = pg_col1.number_input("Trang", min_value=1, max_value=max(pages, 1), value=1, step=1)
pg_col2.markdown(f"<span class='badge'>Tổng: {total} dòng • {pages} trang</span>", unsafe_allow_html=True)

start = (page - 1) * page_size
end   = start + page_size
show  = filtered.iloc[start:end].reset_index(drop=True)

# Header
H = st.columns([0.35, 1.0, 1.8, 1.2, 1.1, 1.0, 1.6, 0.7, 0.7])
H[0].markdown("**#**")
H[1].markdown("**Số văn bản**")
H[2].markdown("**Tiêu đề**")
H[3].markdown("**Cơ quan**")
H[4].markdown("**Lĩnh vực**")
H[5].markdown("**Ngày ban hành**")
H[6].markdown("**File**")
H[7].markdown("**⬇️ Tải**")
H[8].markdown("**🗑 Xóa**")

for idx, row in show.iterrows():
    dropbox_path = _clean_path(row.get("File Dropbox", ""))
    file_name    = os.path.basename(dropbox_path) if dropbox_path.startswith("/") else ""

    c = st.columns([0.35, 1.0, 1.8, 1.2, 1.1, 1.0, 1.6, 0.7, 0.7])
    c[0].write(f"**{start+idx+1}**")
    c[1].write(row.get("Số văn bản", ""))
    c[2].write(row.get("Tiêu đề", ""))
    c[3].write(row.get("Cơ quan", ""))
    c[4].write(row.get("Lĩnh vực", ""))
    c[5].write(row.get("Ngày ban hành", ""))
    c[6].write(file_name or "-")

    # ⬇️ Tải
    with c[7].container():
        st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
        if dropbox_path and dropbox_path.startswith("/"):
            try:
                file_bytes = download_bytes_from_dropbox(dropbox_path)
                st.download_button("⬇️", data=file_bytes, file_name=file_name or "file",
                                   mime="application/octet-stream", key=f"dl_{dropbox_path}")
            except Exception:
                st.button("⚠️", key=f"warn_{dropbox_path}", disabled=True)
        else:
            st.button("—", key=f"dl_dis_{idx}", disabled=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 🗑 Xóa
    with c[8].container():
        st.markdown('<div class="btn-cell">', unsafe_allow_html=True)
        if dropbox_path and st.button("🗑", key=f"del_{dropbox_path}"):
            try:
                delete_file_from_dropbox(dropbox_path)
            except Exception as e:
                st.error(f"Lỗi xóa Dropbox: {e}")

            # Xóa khỏi CSV
            all_df = _read_csv()
            all_df = all_df[all_df["File Dropbox"].apply(_clean_path) != dropbox_path]
            all_df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
            st.success(f"Đã xóa: {file_name}")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
