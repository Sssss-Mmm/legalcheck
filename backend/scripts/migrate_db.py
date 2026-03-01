import sqlite3
import os

db_path = "/home/sssssmmm/legalcheck/backend/legalcheck.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"DB file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Check if column already exists
        cur.execute("PRAGMA table_info(chat_sessions)")
        columns = [info[1] for info in cur.fetchall()]
        
        if "is_bookmarked" not in columns:
            print("Adding is_bookmarked column to chat_sessions table...")
            cur.execute("ALTER TABLE chat_sessions ADD COLUMN is_bookmarked BOOLEAN DEFAULT 0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column is_bookmarked already exists.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
