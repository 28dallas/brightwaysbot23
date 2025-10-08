#!/usr/bin/env python3
"""
Quick fix for balance display issue
"""

import sqlite3
import os
import sys
from datetime import datetime

def fix_balance_issue():
    """Fix the balance display issue"""
    
    print("🔧 Fixing balance display issue...")
    
    # 1. Check database
    db_path = 'backend/trading.db'
    if not os.path.exists(db_path):
        db_path = 'trading.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found!")
        return False
    
    # 2. Fix user balances
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check users table
        cursor.execute("SELECT id, email, balance, account_type FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("❌ No users found!")
            return False
        
        print(f"📊 Found {len(users)} users")
        
        # Fix null/zero balances
        fixed_count = 0
        for user_id, email, balance, account_type in users:
            if balance is None or balance == 0:
                new_balance = 10000.0 if account_type == 'demo' else 1000.0
                cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                print(f"✅ Fixed balance for {email}: ${new_balance}")
                fixed_count += 1
            else:
                print(f"✓ {email}: ${balance} ({account_type})")
        
        if fixed_count > 0:
            conn.commit()
            print(f"💾 Updated {fixed_count} user balances")
        
        conn.close()
        
        # 3. Check backend port configuration
        print("\n🔍 Checking backend configuration...")
        
        # Check main_new.py for port
        main_files = ['backend/main_new.py', 'main_new.py']
        for main_file in main_files:
            if os.path.exists(main_file):
                with open(main_file, 'r') as f:
                    content = f.read()
                    if 'port=8001' in content:
                        print("✅ Backend configured for port 8001")
                    elif 'port=8000' in content:
                        print("⚠️  Backend configured for port 8000 (frontend expects 8001)")
                        print("   Update frontend or backend port configuration")
                    break
        
        # 4. Check frontend configuration
        print("\n🔍 Checking frontend configuration...")
        
        app_js_path = 'frontend/src/App.js'
        if os.path.exists(app_js_path):
            with open(app_js_path, 'r') as f:
                content = f.read()
                if 'localhost:8001' in content:
                    print("✅ Frontend configured for port 8001")
                elif 'localhost:8000' in content:
                    print("⚠️  Frontend configured for port 8000")
        
        print("\n🚀 Quick Start Instructions:")
        print("1. Start backend: cd backend && python main_new.py")
        print("2. Start frontend: cd frontend && npm start")
        print("3. Check browser console for any errors")
        print("4. Verify WebSocket connection is working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    success = fix_balance_issue()
    if success:
        print("\n✅ Balance issue fix completed!")
    else:
        print("\n❌ Failed to fix balance issue")