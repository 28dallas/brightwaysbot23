import React, { useState, useEffect } from 'react';
import './IntegrationPanel.css';

const IntegrationPanel = () => {
  const [tvStatus, setTvStatus] = useState('inactive');
  const [mt5Status, setMt5Status] = useState('disconnected');
  const [mt5Config, setMt5Config] = useState({
    login: '',
    password: '',
    server: ''
  });
  const [webhookUrl, setWebhookUrl] = useState('');

  useEffect(() => {
    fetchIntegrationStatus();
    generateWebhookUrl();
  }, []);

  const fetchIntegrationStatus = async () => {
    try {
      const response = await fetch('/api/integrations/status');
      const data = await response.json();
      setTvStatus(data.tradingview.status);
      setMt5Status(data.mt5.status);
    } catch (error) {
      console.error('Failed to fetch integration status:', error);
    }
  };

  const generateWebhookUrl = () => {
    const baseUrl = window.location.origin;
    setWebhookUrl(`${baseUrl}/api/integrations/tradingview/webhook`);
  };

  const connectMT5 = async () => {
    try {
      const response = await fetch('/api/integrations/mt5/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mt5Config)
      });
      
      if (response.ok) {
        setMt5Status('connected');
        alert('MT5 connected successfully!');
      } else {
        alert('MT5 connection failed');
      }
    } catch (error) {
      alert('MT5 connection error: ' + error.message);
    }
  };

  const startMT5Monitoring = async () => {
    try {
      await fetch('/api/integrations/mt5/start-monitoring', {
        method: 'POST'
      });
      alert('MT5 monitoring started');
    } catch (error) {
      alert('Failed to start MT5 monitoring');
    }
  };

  const disconnectMT5 = async () => {
    try {
      await fetch('/api/integrations/mt5/disconnect', {
        method: 'POST'
      });
      setMt5Status('disconnected');
      alert('MT5 disconnected');
    } catch (error) {
      alert('Failed to disconnect MT5');
    }
  };

  const copyWebhookUrl = () => {
    navigator.clipboard.writeText(webhookUrl);
    alert('Webhook URL copied to clipboard!');
  };

  return (
    <div className="integration-panel">
      <h2>Platform Integrations</h2>
      
      {/* TradingView Integration */}
      <div className="integration-section">
        <h3>📈 TradingView Integration</h3>
        <div className={`status-indicator ${tvStatus}`}>
          Status: {tvStatus}
        </div>
        
        <div className="webhook-section">
          <label>Webhook URL:</label>
          <div className="webhook-url-container">
            <input 
              type="text" 
              value={webhookUrl} 
              readOnly 
              className="webhook-url"
            />
            <button onClick={copyWebhookUrl} className="copy-btn">
              Copy
            </button>
          </div>
        </div>
        
        <div className="setup-instructions">
          <h4>Setup Instructions:</h4>
          <ol>
            <li>Create alert in TradingView</li>
            <li>Set webhook URL to: <code>{webhookUrl}</code></li>
            <li>Use JSON format with fields: symbol, action, price, strategy</li>
            <li>Example: <code>{`{"symbol":"EURUSD","action":"buy","price":1.0850,"strategy":"MA Cross"}`}</code></li>
          </ol>
        </div>
      </div>

      {/* MetaTrader 5 Integration */}
      <div className="integration-section">
        <h3>🔧 MetaTrader 5 Integration</h3>
        <div className={`status-indicator ${mt5Status}`}>
          Status: {mt5Status}
        </div>
        
        {mt5Status === 'disconnected' && (
          <div className="mt5-config">
            <h4>MT5 Connection Settings:</h4>
            <input
              type="number"
              placeholder="Login"
              value={mt5Config.login}
              onChange={(e) => setMt5Config({...mt5Config, login: e.target.value})}
            />
            <input
              type="password"
              placeholder="Password"
              value={mt5Config.password}
              onChange={(e) => setMt5Config({...mt5Config, password: e.target.value})}
            />
            <input
              type="text"
              placeholder="Server (e.g., MetaQuotes-Demo)"
              value={mt5Config.server}
              onChange={(e) => setMt5Config({...mt5Config, server: e.target.value})}
            />
            <button onClick={connectMT5} className="connect-btn">
              Connect to MT5
            </button>
          </div>
        )}
        
        {mt5Status === 'connected' && (
          <div className="mt5-controls">
            <button onClick={startMT5Monitoring} className="monitor-btn">
              Start Trade Monitoring
            </button>
            <button onClick={disconnectMT5} className="disconnect-btn">
              Disconnect MT5
            </button>
          </div>
        )}
        
        <div className="setup-instructions">
          <h4>Requirements:</h4>
          <ul>
            <li>MetaTrader 5 terminal must be running</li>
            <li>Allow automated trading in MT5 settings</li>
            <li>Trades from MT5 will be copied to Deriv automatically</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default IntegrationPanel;