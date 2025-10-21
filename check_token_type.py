import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('DERIV_API_TOKEN') or "<DEMO_TOKEN>"
print(f"API Token: {'*' * len(token) if token else 'Not set'}")

# Check token format - Deriv tokens have specific patterns
if len(token) < 10:
    print("❌ Token too short")
elif token.startswith('demo_'):
    print("🟡 This appears to be a demo token")
elif any(char.isdigit() for char in token) and any(char.isalpha() for char in token):
    print("✅ Token format looks valid for live trading")
else:
    print("⚠️ Token format unclear")

print("\nTo get your real balance:")
print("1. Go to https://app.deriv.com")
print("2. Settings > API Token")
print("3. Create token with 'Trading' scope")
print("4. Update your .env file")