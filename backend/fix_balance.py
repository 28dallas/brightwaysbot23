#!/usr/bin/env python3

import sqlite3
import os
from datetime import datetime

def fix_user_balances():
    """Check and fix user balances in the database"""
    
    db_path = 'trading.db'
    
    if not os.path.exists(db_path):
        print("Database not found. Creating new database...")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users table doesn't exist. Run the main app first to create tables.")
            return
        
        # Get all users
        cursor.execute("SELECT id, email, balance, account_type FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in database.")
            print("Creating a test user with 10,000 balance...")
            
            # Create a test user
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, balance, account_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                'test@example.com',
                '$2b$12$dummy_hash_for_testing',  # This won't work for login, just for testing
                'Test User',
                10000.0,
                'demo',
                datetime.utcnow()
            ))
            conn.commit()
            print("Test user created with email: test@example.com")
        else:
            print(f"Found {len(users)} users:")
            for user in users:
                user_id, email, balance, account_type = user
                print(f"  ID: {user_id}, Email: {email}, Balance: ${balance}, Type: {account_type}")
                
                # Fix zero balances
                if balance == 0 or balance is None:
                    new_balance = 10000.0
                    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                    print(f"  → Fixed balance for {email}: ${new_balance}")
            
            conn.commit()
            print("Balance fixes applied!")
        
        # Show final state
        cursor.execute("SELECT id, email, balance, account_type FROM users")
        users = cursor.fetchall()
        print("\nFinal user balances:")
        for user in users:
            user_id, email, balance, account_type = user
            print(f"  {email}: ${balance} ({account_type})")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_user_balances()