import React, { useState, useEffect } from 'react';

const TradingModeToggle = () => {
  const [tradingMode, setTradingMode] = useState('demo');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTradingMode();
  }, []);

  const fetchTradingMode = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/trading-mode');
      const data = await response.json();
      setTradingMode(data.trading_mode);
    } catch (error) {
      console.error('Error fetching trading mode:', error);
    }
  };

  const toggleMode = async (newMode) => {
    if (newMode === 'live') {
      const confirmed = window.confirm(
        '⚠️ WARNING: You are switching to LIVE trading mode!\n\n' +
        'This will use REAL MONEY from your Deriv account.\n' +
        'Make sure you have tested thoroughly in demo mode.\n\n' +
        'Are you sure you want to continue?'
      );
      if (!confirmed) return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8001/api/trading-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode })
      });
      
      const data = await response.json();
      setTradingMode(data.trading_mode);
      
      alert(`✅ Switched to ${newMode.toUpperCase()} mode successfully!`);
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
      <div className="flex space-x-3">
        <button
          onClick={() => toggleMode('demo')}
          disabled={loading || tradingMode === 'demo'}
          className={`px-4 py-2 rounded font-medium transition-colors ${
            tradingMode === 'demo'
              ? 'bg-yellow-600 text-white'
              : 'bg-gray-600 hover:bg-yellow-600 text-gray-300'
          } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          📊 Demo Mode
        </button>
        <button
          onClick={() => toggleMode('live')}
          disabled={loading || tradingMode === 'live'}
          className={`px-4 py-2 rounded font-medium transition-colors ${
            tradingMode === 'live'
              ? 'bg-red-600 text-white'
              : 'bg-gray-600 hover:bg-red-600 text-gray-300'
          } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          💰 Live Mode
        </button>
      </div>
      <div className="mt-2 text-sm text-gray-400">
        Current: <span className={`font-semibold ${tradingMode === 'live' ? 'text-red-400' : 'text-yellow-400'}`}>
          {tradingMode.toUpperCase()}
        </span>
        {tradingMode === 'live' && <span className="text-red-400 ml-2">⚠️ REAL MONEY</span>}
      </div>
    </div>
  );
};

export default TradingModeToggle;