import sqlite3

DB_NAME = "sales_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            upload_date TEXT,
            salesman_name TEXT,
            overall_score INTEGER,
            summary TEXT,
            pdf_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_call(filename, upload_date, salesman_name, overall_score, summary, pdf_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO calls (filename, upload_date, salesman_name, overall_score, summary, pdf_path) VALUES (?, ?, ?, ?, ?, ?)",
              (filename, upload_date, salesman_name, overall_score, summary, pdf_path))
    conn.commit()
    conn.close()

def get_all_calls():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM calls ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_call(call_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE id=?", (call_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_call_db(call_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM calls WHERE id=?", (call_id,))
    conn.commit()
    conn.close()
