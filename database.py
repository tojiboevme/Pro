import sqlite3

DB_FILE = "data/campaign.db"

def connect():
    return sqlite3.connect(DB_FILE)

def create_tables():
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            telegram_id INTEGER,
            datetime TEXT,
            random_number INTEGER
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS used_codes (
            code TEXT PRIMARY KEY
        )
        """)

def is_code_used(code: str) -> bool:
    with connect() as db:
        result = db.execute("SELECT 1 FROM used_codes WHERE code = ?", (code,)).fetchone()
        return result is not None

def save_used_code(code: str):
    with connect() as db:
        db.execute("INSERT INTO used_codes (code) VALUES (?)", (code,))

def add_user(phone, code, telegram_id, datetime_str, random_number):
    with connect() as db:
        db.execute("""
            INSERT INTO users (phone, code, telegram_id, datetime, random_number)
            VALUES (?, ?, ?, ?, ?)
        """, (phone, code, telegram_id, datetime_str, random_number))

def get_next_number() -> int:
    with connect() as db:
        result = db.execute("SELECT COUNT(*) FROM users").fetchone()
        return (result[0] or 0) + 1

def export_users_csv(filepath="storage/users.csv"):
    import csv, os
    os.makedirs("storage", exist_ok=True)
    with connect() as db, open(filepath, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['phone', 'code', 'telegram_id', 'datetime', 'random_number'])
        for row in db.execute("SELECT phone, code, telegram_id, datetime, random_number FROM users"):
            writer.writerow(row)

def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'phone': row[1],
            'code': row[2],
            'telegram_id': row[3],
            'datetime': row[4],
            'random_number': row[5]
        }
    return None
