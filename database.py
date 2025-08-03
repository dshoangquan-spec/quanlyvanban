import sqlite3

def init_db():
    conn = sqlite3.connect("vanban.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vanban (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        so_van_ban TEXT,
        tieu_de TEXT,
        ngay_ban_hanh TEXT,
        co_quan TEXT,
        linh_vuc TEXT,
        file_dinh_kem TEXT
    )""")
    conn.commit()
    conn.close()
