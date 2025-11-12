import React, { useState, useEffect } from 'react';

const TradingModeToggle = () => {
  const [tradingMode, setTradingMode] = useState('demo');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTradingMode();
  }, []);

  const fetchTradingMode = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/trading-mode', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      const data = await response.json();
      setTradingMode(data.trading_mode || 'demo');
    } catch (error) {
      console.error('Error fetching trading mode:', error);
      setTradingMode('demo');
    }
  };

  const toggleMode = async (newMode) => {
    if (newMode === 'live') {
      const confirmed = window.confirm(
        '⚠️ WARNING: You are switching to LIVE trading mode!\n\n' +
        'This will use REAL MONEY from your Deriv account.\n' +
        'Make sure you have your API token set up and tested in demo mode.\n\n' +
        'Are you sure you want to continue?'
      );
      if (!confirmed) return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/trading-mode', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ mode: newMode })
      });
      
      if (response.ok) {
        const data = await response.json();
        setTradingMode(data.trading_mode);
        alert(`✅ Switched to ${newMode.toUpperCase()} mode successfully!`);
        
        // Refresh the page to update all components
        window.location.reload();
      } else {
        const error = await response.json();
        alert(`❌ Failed to switch: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error toggling trading mode:', error);
      alert('❌ Failed to switch trading mode');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg">
      <h3 className="text-lg font-semibold mb-3">Trading Mode</h3>
      <div className="flex space-x-2">
        <button
          onClick={() => toggleMode('demo')}
          disabled={loading || (tradingMode || 'demo') === 'demo'}
          className={`flex-1 px-4 py-2 rounded font-medium transition-colors ${
            (tradingMode || 'demo') === 'demo'
              ? 'bg-yellow-600 text-white shadow-lg'
              : 'bg-gray-600 hover:bg-yellow-600 text-gray-300'
          } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          📊 Demo
        </button>
        <button
          onClick={() => toggleMode('live')}
          disabled={loading || (tradingMode || 'demo') === 'live'}
          className={`flex-1 px-4 py-2 rounded font-medium transition-colors ${
            (tradingMode || 'demo') === 'live'
              ? 'bg-red-600 text-white shadow-lg'
              : 'bg-gray-600 hover:bg-red-600 text-gray-300'
          } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          💰 Live
        </button>
      </div>
      <div className="mt-2 text-sm text-gray-400">
        Current: <span className={`font-semibold ${tradingMode === 'live' ? 'text-red-400' : 'text-yellow-400'}`}>
          {(tradingMode || 'demo').toUpperCase()}
        </span>
        {tradingMode === 'live' && <span className="text-red-400 ml-2">⚠️ REAL MONEY</span>}
        {tradingMode === 'demo' && <span className="text-yellow-400 ml-2">📊 VIRTUAL MONEY</span>}
      </div>
      <div className="mt-2 text-xs text-gray-500">
        {(tradingMode || 'demo') === 'demo' 
          ? 'Demo mode uses virtual money for safe testing'
          : 'Live mode uses your real Deriv account balance'
        }
      </div>
    </div>
  );
};

export default TradingModeToggle;
