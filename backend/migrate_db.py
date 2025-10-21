import sqlite3

def migrate_db():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()

    # Check if app_id column exists in users
    cursor.execute("PRAGMA table_info(users);")
    users_columns = [col[1] for col in cursor.fetchall()]
    if 'app_id' not in users_columns:
        print("Adding app_id column to users table")
        cursor.execute("ALTER TABLE users ADD COLUMN app_id TEXT;")

    # Check if strategy_id column exists in trades
    cursor.execute("PRAGMA table_info(trades);")
    trades_columns = [col[1] for col in cursor.fetchall()]
    if 'strategy_id' not in trades_columns:
        print("Adding strategy_id column to trades table")
        cursor.execute("ALTER TABLE trades ADD COLUMN strategy_id INTEGER REFERENCES strategies(id);")

    if 'confidence' not in trades_columns:
        print("Adding confidence column to trades table")
        cursor.execute("ALTER TABLE trades ADD COLUMN confidence REAL;")

    # Check if symbol column exists in ticks
    cursor.execute("PRAGMA table_info(ticks);")
    ticks_columns = [col[1] for col in cursor.fetchall()]
    if 'symbol' not in ticks_columns:
        print("Adding symbol column to ticks table")
        cursor.execute("ALTER TABLE ticks ADD COLUMN symbol TEXT DEFAULT 'R_100';")

    conn.commit()
    conn.close()
    print("Migration completed")

if __name__ == "__main__":
    migrate_db()
