import sqlite3

def check_ticks_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ticks);")
    columns = cursor.fetchall()
    conn.close()
    print("Ticks table columns:")
    for col in columns:
        print(col)

if __name__ == "__main__":
    check_ticks_schema()
