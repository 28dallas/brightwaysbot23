import sqlite3

def check_trades_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trades);")
    columns = cursor.fetchall()
    conn.close()
    print("Trades table columns:")
    for col in columns:
        print(col)

if __name__ == "__main__":
    check_trades_schema()
