import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnhancedStrategyBuilder({ onSaveStrategy }) {
  const [strategy, setStrategy] = useState({
    name: '',
    type: 'volatility_breakout',
    risk_percent: 2,
    stop_loss: 5,
    take_profit: 10,
    trade_frequency: 'medium',
    parameters: {}
  });

  const [backtestResults, setBacktestResults] = useState(null);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [savedStrategies, setSavedStrategies] = useState([]);

  const presetStrategies = [
    { 
      name: 'Volatility Breakout', 
      type: 'volatility_breakout',
      description: 'Trades on high volatility breakouts with momentum',
      parameters: { volatility_threshold: 0.02, momentum_period: 5 }
    },
    { 
      name: 'Trend Following', 
      type: 'trend_following',
      description: 'Follows established trends with moving averages',
      parameters: { ma_fast: 10, ma_slow: 20, trend_strength: 0.5 }
    },
    { 
      name: 'Mean Reversion', 
      type: 'mean_reversion',
      description: 'Trades against extreme price movements',
      parameters: { deviation_threshold: 2, reversion_period: 15 }
    },
    { 
      name: 'AI Pattern Recognition', 
      type: 'ai_pattern',
      description: 'Uses AI to identify recurring patterns',
      parameters: { pattern_length: 10, confidence_threshold: 0.7 }
    }
  ];

  useEffect(() => {
    fetchSavedStrategies();
  }, []);

  const fetchSavedStrategies = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/strategies', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setSavedStrategies(data.strategies || []);
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };

  const handleSaveStrategy = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/strategy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(strategy)
      });
      
      const data = await response.json();
      if (data.success) {
        onSaveStrategy(strategy);
        fetchSavedStrategies();
        alert('Strategy saved successfully!');
      }
    } catch (error) {
      console.error('Error saving strategy:', error);
    }
  };

  const runBacktest = async () => {
    setIsBacktesting(true);
    
    // Simulate backtesting with mock data
    setTimeout(() => {
      const mockResults = {
        total_trades: Math.floor(Math.random() * 100) + 50,
        win_rate: Math.random() * 40 + 45, // 45-85%
        total_return: (Math.random() - 0.3) * 1000, // -300 to +700
        max_drawdown: Math.random() * 200 + 50,
        sharpe_ratio: Math.random() * 2 + 0.5,
        equity_curve: Array.from({length: 30}, (_, i) => ({
          day: i + 1,
          equity: 10000 + (Math.random() - 0.4) * 2000 * i
        }))
      };
      
      setBacktestResults(mockResults);
      setIsBacktesting(false);
    }, 2000);
  };

  const selectedPreset = presetStrategies.find(p => p.type === strategy.type);

  return (
    <div className="space-y-6">
      {/* Strategy Builder */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold text-white mb-4">🛠️ Strategy Builder</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-white mb-2">Strategy Name</label>
              <input
                type="text"
                value={strategy.name}
                onChange={(e) => setStrategy({...strategy, name: e.target.value})}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                placeholder="My Awesome Strategy"
              />
            </div>

            <div>
              <label className="block text-white mb-2">Strategy Type</label>
              <select
                value={strategy.type}
                onChange={(e) => setStrategy({...strategy, type: e.target.value})}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                {presetStrategies.map(preset => (
                  <option key={preset.type} value={preset.type}>{preset.name}</option>
                ))}
              </select>
              {selectedPreset && (
                <p className="text-gray-400 text-sm mt-2">{selectedPreset.description}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-white mb-2">Risk % per Trade</label>
                <input
                  type="number"
                  min="0.1"
                  max="10"
                  step="0.1"
                  value={strategy.risk_percent}
                  onChange={(e) => setStrategy({...strategy, risk_percent: parseFloat(e.target.value)})}
                  className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-white mb-2">Trade Frequency</label>
                <select
                  value={strategy.trade_frequency}
                  onChange={(e) => setStrategy({...strategy, trade_frequency: e.target.value})}
                  className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                >
                  <option value="low">Low (1-3 trades/day)</option>
                  <option value="medium">Medium (4-8 trades/day)</option>
                  <option value="high">High (9+ trades/day)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-white mb-2">Stop Loss %</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={strategy.stop_loss}
                  onChange={(e) => setStrategy({...strategy, stop_loss: parseInt(e.target.value)})}
                  className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-white mb-2">Take Profit %</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={strategy.take_profit}
                  onChange={(e) => setStrategy({...strategy, take_profit: parseInt(e.target.value)})}
                  className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={runBacktest}
                disabled={isBacktesting}
                className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white p-3 rounded font-medium disabled:opacity-50"
              >
                {isBacktesting ? '🔄 Running Backtest...' : '📊 Run Backtest'}
              </button>
              <button
                onClick={handleSaveStrategy}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white p-3 rounded font-medium"
              >
                💾 Save Strategy
              </button>
            </div>
          </div>

          {/* Strategy Parameters */}
          <div className="bg-gray-700 p-4 rounded-lg">
            <h3 className="text-white font-semibold mb-3">Advanced Parameters</h3>
            {selectedPreset && (
              <div className="space-y-3">
                {Object.entries(selectedPreset.parameters).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-gray-300 text-sm mb-1 capitalize">
                      {key.replace('_', ' ')}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      defaultValue={value}
                      className="w-full p-2 bg-gray-600 text-white rounded border border-gray-500 text-sm"
                      onChange={(e) => setStrategy({
                        ...strategy, 
                        parameters: {...strategy.parameters, [key]: parseFloat(e.target.value)}
                      })}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Backtest Results */}
      {backtestResults && (
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">📈 Backtest Results</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-gray-700 p-3 rounded text-center">
              <div className="text-2xl font-bold text-white">{backtestResults.total_trades}</div>
              <div className="text-sm text-gray-400">Total Trades</div>
            </div>
            <div className="bg-gray-700 p-3 rounded text-center">
              <div className="text-2xl font-bold text-green-400">{backtestResults.win_rate.toFixed(1)}%</div>
              <div className="text-sm text-gray-400">Win Rate</div>
            </div>
            <div className="bg-gray-700 p-3 rounded text-center">
              <div className={`text-2xl font-bold ${backtestResults.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${backtestResults.total_return.toFixed(0)}
              </div>
              <div className="text-sm text-gray-400">Total Return</div>
            </div>
            <div className="bg-gray-700 p-3 rounded text-center">
              <div className="text-2xl font-bold text-red-400">${backtestResults.max_drawdown.toFixed(0)}</div>
              <div className="text-sm text-gray-400">Max Drawdown</div>
            </div>
            <div className="bg-gray-700 p-3 rounded text-center">
              <div className="text-2xl font-bold text-blue-400">{backtestResults.sharpe_ratio.toFixed(2)}</div>
              <div className="text-sm text-gray-400">Sharpe Ratio</div>
            </div>
          </div>

          <div className="bg-gray-700 p-4 rounded">
            <h4 className="text-white font-semibold mb-3">Equity Curve</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={backtestResults.equity_curve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="day" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                />
                <Line type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Saved Strategies */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h3 className="text-white text-lg font-semibold mb-4">💾 Saved Strategies</h3>
        {savedStrategies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {savedStrategies.map((savedStrategy) => (
              <div key={savedStrategy.id} className="bg-gray-700 p-4 rounded-lg">
                <h4 className="text-white font-semibold">{savedStrategy.name}</h4>
                <p className="text-gray-400 text-sm capitalize">{savedStrategy.type.replace('_', ' ')}</p>
                <div className="mt-2 text-sm text-gray-300">
                  Risk: {savedStrategy.risk_percent}% | SL: {savedStrategy.stop_loss}% | TP: {savedStrategy.take_profit}%
                </div>
                <div className="mt-3 flex space-x-2">
                  <button className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                    Load
                  </button>
                  <button className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm">
                    {savedStrategy.is_active ? 'Active' : 'Activate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">No saved strategies yet. Create your first strategy above!</p>
        )}
      </div>
    </div>
  );
}
