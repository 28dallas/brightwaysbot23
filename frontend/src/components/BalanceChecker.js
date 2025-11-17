import React, { useState } from 'react';

const BalanceChecker = ({ onBalanceUpdate }) => {


  const [apiToken, setApiToken] = useState('');
  const [appId, setAppId] = useState('1089');
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [accountType, setAccountType] = useState('');

  const fetchBalance = async () => {
    if (!apiToken.trim()) {
      setError('Please enter your Deriv API token');
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      setError('Please login first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8001/api/balance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          api_token: apiToken.trim(),
          app_id: appId.trim() || '1089'
        })
      });

      const data = await response.json();

      if (data.success) {
        setBalance(data.balance);
        setAccountType(data.account_type);
        setError('');
        
        // Save token to user and update dashboard
        if (onBalanceUpdate) {
          onBalanceUpdate({
            balance: data.balance,
            accountType: data.account_type,
            apiToken: apiToken.trim(),
            appId: appId.trim() || '1089'
          });
        }
      } else {
        setError(data.message || 'Failed to fetch balance');
        setBalance(null);
      }
    } catch (err) {
      setError('Connection error. Make sure the backend is running.');
      setBalance(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-gray-800 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center text-white">Check Deriv Balance</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Deriv API Token *
          </label>
          <input
            type="text"
            value={apiToken}
            onChange={(e) => setApiToken(e.target.value)}
            placeholder="Enter your Deriv API token"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            App ID (optional)
          </label>
          <input
            type="text"
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            placeholder="1089"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          onClick={fetchBalance}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed"
        >
          {loading ? 'Fetching Balance...' : 'Get Balance'}
        </button>

        {error && (
          <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {balance !== null && (
          <div className="p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            <h3 className="font-semibold">Balance Retrieved Successfully!</h3>
            <p className="text-lg font-bold">${balance.toFixed(2)} USD</p>
            <p className="text-sm">Account Type: {accountType}</p>
          </div>
        )}
      </div>

      <div className="mt-6 text-xs text-gray-400">
        <p>• Your API token is used only to fetch your balance</p>
        <p>• Get your API token from Deriv.com → Settings → API Token</p>
        <p>• Make sure your token has 'Read' permissions</p>
      </div>
    </div>
  );
};

export default BalanceChecker;
