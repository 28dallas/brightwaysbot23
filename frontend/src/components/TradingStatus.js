import React, { useState, useEffect } from 'react';

const TradingStatus = () => {
  const [activeTrades, setActiveTrades] = useState([]);

  useEffect(() => {
    fetchActiveTrades();
    const interval = setInterval(fetchActiveTrades, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchActiveTrades = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8001/api/trades/active', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setActiveTrades(data.trades || []);
      }
    } catch (error) {
      console.error('Error fetching active trades:', error);
    }
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg">
      <h3 className="text-lg font-semibold mb-3">Active Trades</h3>
      {activeTrades.length === 0 ? (
        <p className="text-gray-400 text-sm">No active trades</p>
      ) : (
        <div className="space-y-2">
          {activeTrades.map(trade => (
            <div key={trade.id} className="bg-gray-700 p-3 rounded flex justify-between items-center">
              <div>
                <div className="text-sm font-medium">{trade.contract_type}</div>
                <div className="text-xs text-gray-400">
                  ${trade.stake} • {trade.is_demo ? 'Demo' : 'Live'}
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-medium ${
                  trade.result === 'pending' ? 'text-yellow-400' :
                  trade.result === 'win' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {trade.result.toUpperCase()}
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(trade.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TradingStatus;