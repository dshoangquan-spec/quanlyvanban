# app.py
import streamlit as st
import sqlite3
import pandas as pd
from database import init_db

init_db()

st.set_page_config(page_title="📚 Quản lý Văn bản", layout="wide")
st.title("📚 Quản lý Văn bản Pháp luật")

# Kết nối CSDL
conn = sqlite3.connect("vanban.db")
cursor = conn.cursor()

menu = ["📄 Thêm văn bản", "🔍 Tra cứu", "📤 Xuất Excel"]
choice = st.sidebar.selectbox("Chức năng", menu)

# Thêm văn bản
if choice == "📄 Thêm văn bản":
    with st.form("form_vanban"):
        so_van_ban = st.text_input("Số văn bản")
        tieu_de = st.text_input("Tiêu đề")
        ngay_ban_hanh = st.date_input("Ngày ban hành")
        co_quan = st.text_input("Cơ quan ban hành")
        linh_vuc = st.text_input("Lĩnh vực")
        file_dinh_kem = st.file_uploader("Tải file đính kèm", type=["pdf", "docx"])
        submitted = st.form_submit_button("Lưu văn bản")

        if submitted:
            # Có thể lưu file vào thư mục uploads/ ở đây
            cursor.execute("INSERT INTO vanban (so_van_ban, tieu_de, ngay_ban_hanh, co_quan, linh_vuc, file_dinh_kem) VALUES (?, ?, ?, ?, ?, ?)",
                           (so_van_ban, tieu_de, ngay_ban_hanh.strftime("%Y-%m-%d"), co_quan, linh_vuc, file_dinh_kem.name if file_dinh_kem else None))
            conn.commit()
            st.success("✅ Đã lưu văn bản!")

# Tra cứu
elif choice == "🔍 Tra cứu":
    df = pd.read_sql_query("SELECT * FROM vanban", conn)
    
    st.dataframe(df, use_container_width=True)
    
    co_quan = st.selectbox("Lọc theo cơ quan", ["Tất cả"] + sorted(df["co_quan"].dropna().unique().tolist()))
    if co_quan != "Tất cả":
        df = df[df["co_quan"] == co_quan]
        st.dataframe(df, use_container_width=True)

# Xuất Excel
elif choice == "📤 Xuất Excel":
    df = pd.read_sql_query("SELECT * FROM vanban", conn)
    excel_file = "vanban_export.xlsx"
    df.to_excel(excel_file, index=False)
    with open(excel_file, "rb") as f:
        st.download_button("📥 Tải xuống danh sách", f, file_name=excel_file)

conn.close()
