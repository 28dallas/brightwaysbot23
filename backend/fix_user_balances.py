#!/usr/bin/env python3
"""
Fix user balances - ensure all users have proper balance values
"""

from models.database import SessionLocal, User

def fix_user_balances():
    db = SessionLocal()
    try:
        # Find users with null balances
        users_with_null_balance = db.query(User).filter(User.balance.is_(None)).all()
        
        print(f"Found {len(users_with_null_balance)} users with null balance")
        
        for user in users_with_null_balance:
            # Set default balance based on account type
            default_balance = 10000.0 if user.account_type == 'demo' else 0.0
            user.balance = default_balance
            print(f"Fixed balance for user {user.email}: {default_balance}")
        
        # Also check for users with 0 balance in demo accounts
        demo_users_zero_balance = db.query(User).filter(
            User.account_type == 'demo',
            User.balance == 0.0
        ).all()
        
        print(f"Found {len(demo_users_zero_balance)} demo users with 0 balance")
        
        for user in demo_users_zero_balance:
            user.balance = 10000.0
            print(f"Reset demo balance for user {user.email}: 10000.0")
        
        db.commit()
        print("All user balances fixed successfully!")
        
    except Exception as e:
        print(f"Error fixing balances: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_balances()