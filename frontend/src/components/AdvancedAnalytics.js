import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, BarChart, Bar, ResponsiveContainer } from 'recharts';

export default function AdvancedAnalytics({ trades, balance, initialBalance }) {
  const [advancedMetrics, setAdvancedMetrics] = useState(null);
  const [aiPrediction, setAiPrediction] = useState(null);

  useEffect(() => {
    fetchAdvancedMetrics();
    fetchAIPrediction();
  }, []);

  const fetchAdvancedMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/analytics/advanced', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setAdvancedMetrics(data);
    } catch (error) {
      console.error('Error fetching advanced metrics:', error);
    }
  };

  const fetchAIPrediction = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/ai/prediction', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setAiPrediction(data);
    } catch (error) {
      console.error('Error fetching AI prediction:', error);
    }
  };

  const profitData = trades.slice(0, 30).reverse().map((trade, index) => ({
    trade: index + 1,
    cumulative: trades.slice(index).reduce((sum, t) => sum + (t.pnl || 0), initialBalance),
    pnl: trade.pnl || 0
  }));

  const winLossData = [
    { name: 'Wins', value: trades.filter(t => t.result === 'win').length, color: '#10b981' },
    { name: 'Losses', value: trades.filter(t => t.result === 'lose').length, color: '#ef4444' }
  ];

  const hourlyData = trades.reduce((acc, trade) => {
    const hour = new Date(trade.timestamp).getHours();
    acc[hour] = (acc[hour] || 0) + (trade.pnl || 0);
    return acc;
  }, {});

  const hourlyChart = Object.entries(hourlyData).map(([hour, pnl]) => ({
    hour: `${hour}:00`,
    pnl: pnl
  }));

  const totalPnL = balance - initialBalance;
  const winRate = trades.length > 0 ? (trades.filter(t => t.result === 'win').length / trades.length * 100) : 0;

  return (
    <div className="space-y-6">
      {/* AI Prediction Card */}
      {aiPrediction && (
        <div className="bg-gradient-to-r from-purple-800 to-blue-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">🤖 AI Market Prediction</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{aiPrediction.prediction}</div>
              <div className="text-sm text-gray-300">Next Digit</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">{(aiPrediction.confidence * 100).toFixed(1)}%</div>
              <div className="text-sm text-gray-300">Confidence</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${aiPrediction.signal === 'buy' ? 'text-green-400' : aiPrediction.signal === 'sell' ? 'text-red-400' : 'text-yellow-400'}`}>
                {aiPrediction.signal?.toUpperCase()}
              </div>
              <div className="text-sm text-gray-300">Signal</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">{aiPrediction.volatility?.toFixed(3)}</div>
              <div className="text-sm text-gray-300">Volatility</div>
            </div>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
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
          <h3 className="text-gray-400 text-sm">Profit Factor</h3>
          <div className="text-2xl font-bold text-blue-400">
            {advancedMetrics?.profit_factor?.toFixed(2) || '0.00'}
          </div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Max Drawdown</h3>
          <div className="text-2xl font-bold text-red-400">
            ${advancedMetrics?.max_drawdown?.toFixed(2) || '0.00'}
          </div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-gray-400 text-sm">Avg Win</h3>
          <div className="text-2xl font-bold text-green-400">
            ${advancedMetrics?.avg_win?.toFixed(2) || '0.00'}
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Equity Curve</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={profitData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="trade" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Line type="monotone" dataKey="cumulative" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Win/Loss Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={winLossData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({name, value, percent}) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
              >
                {winLossData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Hourly Performance</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={hourlyChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="hour" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Bar dataKey="pnl" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white text-lg font-semibold mb-4">Trade P&L Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={profitData.slice(-20)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="trade" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Bar dataKey="pnl" fill={(entry) => entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Export Options */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h3 className="text-white text-lg font-semibold mb-4">Export Reports</h3>
        <div className="flex space-x-4">
          <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
            📊 Export CSV
          </button>
          <button className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded">
            📄 Export PDF
          </button>
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
            📈 Share Report
          </button>
        </div>
      </div>
    </div>
  );
}
