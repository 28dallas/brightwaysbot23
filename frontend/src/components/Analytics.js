import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell } from 'recharts';

export default function Analytics({ trades, balance, initialBalance }) {
  const profitData = trades.slice(0, 20).reverse().map((trade, index) => ({
    trade: index + 1,
    cumulative: trades.slice(index).reduce((sum, t) => sum + t.pnl, initialBalance)
  }));

  const winLossData = [
    { name: 'Wins', value: trades.filter(t => t.result === 'win').length, color: '#10b981' },
    { name: 'Losses', value: trades.filter(t => t.result === 'lose').length, color: '#ef4444' }
  ];

  const totalPnL = balance - initialBalance;
  const winRate = trades.length > 0 ? (trades.filter(t => t.result === 'win').length / trades.length * 100) : 0;
  const avgTrade = trades.length > 0 ? trades.reduce((sum, t) => sum + t.pnl, 0) / trades.length : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Total P&L</h3>
          <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${totalPnL.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Win Rate</h3>
          <div className="text-2xl font-bold text-white">{winRate.toFixed(1)}%</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Total Trades</h3>
          <div className="text-2xl font-bold text-white">{trades.length}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Avg Trade</h3>
          <div className={`text-2xl font-bold ${avgTrade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${avgTrade.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Profit Over Time</h3>
          <LineChart width={400} height={200} data={profitData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="trade" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="cumulative" stroke="#10b981" strokeWidth={2} />
          </LineChart>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Win/Loss Ratio</h3>
          <PieChart width={400} height={200}>
            <Pie
              data={winLossData}
              cx={200}
              cy={100}
              outerRadius={80}
              dataKey="value"
              label={({name, value}) => `${name}: ${value}`}
            >
              {winLossData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </div>
      </div>
    </div>
  );
}