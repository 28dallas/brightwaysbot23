import React, { useState } from 'react';

const AutoTrading = () => {
  const [isActive, setIsActive] = useState(false);
  const [strategy, setStrategy] = useState('ai_confidence');
  const [minConfidence, setMinConfidence] = useState(0.7);
  const [contractType, setContractType] = useState('DIGITEVEN');
  const [symbol, setSymbol] = useState('R_100');

  const startAutoTrading = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/auto-trading/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: strategy,
          type: 'ai_based',
          min_confidence: minConfidence,
          contract_type: contractType,
          symbol: symbol,
          duration: 5,
          duration_unit: 't',
          check_interval: 30,
          trade_interval: 60
        })
      });

      if (response.ok) {
        setIsActive(true);
        alert('Auto trading started!');
      }
    } catch (error) {
      console.error('Error starting auto trading:', error);
    }
  };

  const stopAutoTrading = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/auto-trading/stop', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setIsActive(false);
        alert('Auto trading stopped!');
      }
    } catch (error) {
      console.error('Error stopping auto trading:', error);
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg">
      <h2 className="text-xl font-semibold mb-4">Auto Trading</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Strategy</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          >
            <option value="ai_confidence">AI Confidence</option>
            <option value="martingale">Martingale</option>
            <option value="anti_martingale">Anti-Martingale</option>
            <option value="fibonacci">Fibonacci</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Min Confidence</label>
          <input
            type="range"
            min="0.5"
            max="0.9"
            step="0.05"
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            className="w-full"
          />
          <span className="text-sm text-gray-400">{(minConfidence * 100).toFixed(0)}%</span>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Contract Type</label>
          <select
            value={contractType}
            onChange={(e) => setContractType(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          >
            <option value="DIGITEVEN">Even Digits</option>
            <option value="DIGITODD">Odd Digits</option>
            <option value="CALL">Rise</option>
            <option value="PUT">Fall</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Symbol</label>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          >
            <option value="R_100">Volatility 100</option>
            <option value="R_75">Volatility 75</option>
            <option value="R_50">Volatility 50</option>
            <option value="BOOM1000">Boom 1000</option>
            <option value="CRASH1000">Crash 1000</option>
          </select>
        </div>

        <button
          onClick={isActive ? stopAutoTrading : startAutoTrading}
          className={`w-full px-4 py-2 rounded font-medium ${
            isActive 
              ? 'bg-red-600 hover:bg-red-700' 
              : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {isActive ? 'Stop Auto Trading' : 'Start Auto Trading'}
        </button>

        {isActive && (
          <div className="bg-green-900 p-3 rounded">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
              <span className="text-green-400 text-sm">Auto trading active</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AutoTrading;