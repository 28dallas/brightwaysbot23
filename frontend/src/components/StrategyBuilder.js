import React, { useState } from 'react';

export default function StrategyBuilder({ onSaveStrategy }) {
  const [strategy, setStrategy] = useState({
    name: '',
    type: 'volatility_breakout',
    riskPercent: 2,
    stopLoss: 5,
    takeProfit: 10,
    tradeFrequency: 'medium'
  });

  const presetStrategies = [
    { name: 'Volatility Breakout', type: 'volatility_breakout' },
    { name: 'Trend Following', type: 'trend_following' },
    { name: 'Mean Reversion', type: 'mean_reversion' }
  ];

  return (
    <div className="bg-gray-800 p-6 rounded-lg">
      <h2 className="text-xl font-semibold text-white mb-4">Strategy Builder</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-white mb-2">Strategy Name</label>
          <input
            type="text"
            value={strategy.name}
            onChange={(e) => setStrategy({...strategy, name: e.target.value})}
            className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
            placeholder="My Strategy"
          />
        </div>

        <div>
          <label className="block text-white mb-2">Preset Strategy</label>
          <select
            value={strategy.type}
            onChange={(e) => setStrategy({...strategy, type: e.target.value})}
            className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
          >
            {presetStrategies.map(preset => (
              <option key={preset.type} value={preset.type}>{preset.name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-white mb-2">Risk % per Trade</label>
            <input
              type="number"
              min="0.1"
              max="10"
              step="0.1"
              value={strategy.riskPercent}
              onChange={(e) => setStrategy({...strategy, riskPercent: parseFloat(e.target.value)})}
              className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
            />
          </div>
          <div>
            <label className="block text-white mb-2">Trade Frequency</label>
            <select
              value={strategy.tradeFrequency}
              onChange={(e) => setStrategy({...strategy, tradeFrequency: e.target.value})}
              className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
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
              value={strategy.stopLoss}
              onChange={(e) => setStrategy({...strategy, stopLoss: parseInt(e.target.value)})}
              className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
            />
          </div>
          <div>
            <label className="block text-white mb-2">Take Profit %</label>
            <input
              type="number"
              min="1"
              max="100"
              value={strategy.takeProfit}
              onChange={(e) => setStrategy({...strategy, takeProfit: parseInt(e.target.value)})}
              className="w-full p-2 bg-gray-700 text-white rounded border border-gray-600"
            />
          </div>
        </div>

        <button
          onClick={() => onSaveStrategy(strategy)}
          className="w-full bg-green-600 hover:bg-green-700 text-white p-3 rounded font-medium"
        >
          Save Strategy
        </button>
      </div>
    </div>
  );
}