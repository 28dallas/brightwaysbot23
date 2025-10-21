import React, { useState, useEffect } from 'react';

const AccountSettings = () => {
  const [apiToken, setApiToken] = useState('');
  const [accountType, setAccountType] = useState('demo');
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/balance', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setBalance(data.balance);
      setAccountType(data.account_type);
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  const updateApiToken = async () => {
    setLoading(true);
    setMessage('');
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/account/api-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ api_token: apiToken })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage(data.message);
        setBalance(data.balance);
        setAccountType(data.account_type);
        setApiToken('');
      } else {
        setMessage('Failed to update API token');
      }
    } catch (error) {
      setMessage('Error updating API token');
    } finally {
      setLoading(false);
    }
  };

  const toggleAccount = async () => {
    setLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/account/toggle', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      setBalance(data.balance);
      setAccountType(data.account_type);
      setMessage(`Switched to ${data.account_type} account`);
    } catch (error) {
      setMessage('Failed to toggle account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="account-settings">
      <h3>Account Settings</h3>
      
      <div className="account-info">
        <p><strong>Account Type:</strong> {accountType.toUpperCase()}</p>
        <p><strong>Balance:</strong> ${balance.toFixed(2)}</p>
      </div>

      <div className="api-token-section">
        <h4>Deriv API Token</h4>
        <input
          type="password"
          placeholder="Enter your Deriv API token"
          value={apiToken}
          onChange={(e) => setApiToken(e.target.value)}
          disabled={loading}
        />
        <button onClick={updateApiToken} disabled={loading || !apiToken}>
          {loading ? 'Updating...' : 'Update Token'}
        </button>
        <p className="text-xs text-gray-400 mt-2">
          App ID is not required - the system uses the default App ID automatically.
        </p>
      </div>

      <div className="account-toggle">
        <button onClick={toggleAccount} disabled={loading}>
          Switch to {accountType === 'demo' ? 'Live' : 'Demo'}
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('success') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <div className="help-text">
        <p><strong>How to get your API token:</strong></p>
        <ol>
          <li>Go to <a href="https://app.deriv.com/account/api-token" target="_blank" rel="noopener noreferrer">Deriv API Token page</a></li>
          <li>Create a new token with trading permissions</li>
          <li>Copy and paste it above</li>
        </ol>
      </div>

      <style jsx>{`
        .account-settings {
          max-width: 500px;
          margin: 20px auto;
          padding: 20px;
          border: 1px solid #ddd;
          border-radius: 8px;
          background: white;
        }
        
        .account-info {
          background: #f5f5f5;
          padding: 15px;
          border-radius: 5px;
          margin-bottom: 20px;
        }
        
        .api-token-section {
          margin-bottom: 20px;
        }
        
        .api-token-section input {
          width: 100%;
          padding: 10px;
          margin: 10px 0;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        
        button {
          background: #007bff;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 4px;
          cursor: pointer;
          margin: 5px;
        }
        
        button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        
        .message {
          padding: 10px;
          border-radius: 4px;
          margin: 10px 0;
        }
        
        .message.success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }
        
        .message.error {
          background: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }
        
        .help-text {
          margin-top: 20px;
          padding: 15px;
          background: #e9ecef;
          border-radius: 5px;
          font-size: 14px;
        }
        
        .help-text a {
          color: #007bff;
          text-decoration: none;
        }
      `}</style>
    </div>
  );
};

export default AccountSettings;