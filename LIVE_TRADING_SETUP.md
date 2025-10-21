# Live Trading Setup Guide

To enable live trading where profits and losses reflect on your real Deriv balance, follow these steps:

## 1. Get Your Deriv API Token

1. Go to [Deriv.com](https://deriv.com) and log in to your live account
2. Go to Settings > API token
3. Create a new token with the following scopes:
   - Read
   - Trade
   - Payments
   - Trading information
4. Copy the token (keep it secure!)

## 2. Set Environment Variable

### Windows (PowerShell):
```powershell
$env:DERIV_API_TOKEN = "your_api_token_here"
```

### Windows (Command Prompt):
```cmd
set DERIV_API_TOKEN=your_api_token_here
```

### Linux/Mac:
```bash
export DERIV_API_TOKEN=your_api_token_here
```

## 3. Update .env File

Add this line to your `.env` file:
```
DERIV_API_TOKEN=your_api_token_here
```

## 4. Enable Live Trading

Once the token is set, call the API endpoint:

```bash
curl -X POST http://localhost:8001/api/live-trading/enable
```

## 5. Monitor Trading

- Check active trades: `GET /api/trades/active`
- Check balance: `GET /api/test-token`
- The bot will automatically place trades when AI confidence > 0.7

## Risk Management

The bot includes these safety features:
- Minimum 30 seconds between trades
- Maximum 3 active trades at once
- Maximum stake of $5 per trade
- Only trades when AI confidence > 0.7

## Current Status

Currently, the bot is running in demo mode with balance: $1220.95 USD

To switch to live trading, complete steps 1-3 above and restart the server.
