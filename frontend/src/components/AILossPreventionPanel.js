import React, { useState, useEffect } from 'react';

const AILossPreventionPanel = () => {
  const [marketSafety, setMarketSafety] = useState(null);
  const [marketSentiment, setMarketSentiment] = useState(null);
  const [tradingStatus, setTradingStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAIData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch market safety analysis
      const safetyResponse = await fetch('/api/ai/market-safety', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const safetyData = await safetyResponse.json();
      
      // Fetch market sentiment
      const sentimentResponse = await fetch('/api/ai/market-sentiment', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const sentimentData = await sentimentResponse.json();
      
      // Fetch trading status
      const statusResponse = await fetch('/api/ai/trading-status', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const statusData = await statusResponse.json();
      
      setMarketSafety(safetyData.analysis);
      setMarketSentiment(sentimentData.sentiment);
      setTradingStatus(statusData.status);
      setError(null);
    } catch (err) {
      setError('Failed to fetch AI data');
      console.error('AI data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const controlTrading = async (action, data = {}) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ai/trading-control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ action, ...data })
      });
      
      const result = await response.json();
      if (result.success) {
        fetchAIData(); // Refresh data
      }
      return result;
    } catch (err) {
      console.error('Trading control error:', err);
      return { success: false, error: err.message };
    }
  };

  useEffect(() => {
    fetchAIData();
    const interval = setInterval(fetchAIData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getSafetyColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'LOW': return 'text-green-600 bg-green-100';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-100';
      case 'HIGH': return 'text-orange-600 bg-orange-100';
      case 'CRITICAL': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-3 bg-gray-200 rounded"></div>
            <div className="h-3 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI Loss Prevention Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-2">🤖 AI Loss Prevention System</h2>
        <p className="text-blue-100">Advanced AI models protecting your trades from losses</p>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Market Safety Analysis */}
      {marketSafety && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            🛡️ Market Safety Analysis
            <button 
              onClick={fetchAIData}
              className="ml-auto text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
            >
              Refresh
            </button>
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${getSafetyColor(marketSafety.safety_score)}`}>
                {marketSafety.safety_score?.toFixed(1) || 0}
              </div>
              <div className="text-sm text-gray-600">Safety Score</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {(marketSafety.loss_probability * 100)?.toFixed(1) || 0}%
              </div>
              <div className="text-sm text-gray-600">Loss Probability</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {(marketSafety.profit_probability * 100)?.toFixed(1) || 0}%
              </div>
              <div className="text-sm text-gray-600">Profit Probability</div>
            </div>
            
            <div className="text-center">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(marketSafety.risk_level)}`}>
                {marketSafety.risk_level || 'UNKNOWN'}
              </span>
              <div className="text-sm text-gray-600 mt-1">Risk Level</div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center mb-2">
              <span className={`w-3 h-3 rounded-full mr-2 ${marketSafety.safe_to_trade ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="font-medium">
                {marketSafety.safe_to_trade ? 'SAFE TO TRADE' : 'TRADING BLOCKED'}
              </span>
            </div>
            <p className="text-sm text-gray-700">{marketSafety.recommendation}</p>
          </div>
        </div>
      )}

      {/* Market Sentiment Analysis */}
      {marketSentiment && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">📊 Market Sentiment Analysis</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center">
              <div className="text-xl font-bold text-blue-600">
                {marketSentiment.market_direction || 'NEUTRAL'}
              </div>
              <div className="text-sm text-gray-600">Market Direction</div>
            </div>
            
            <div className="text-center">
              <div className="text-xl font-bold text-purple-600">
                {marketSentiment.overall_sentiment?.toFixed(2) || '0.00'}
              </div>
              <div className="text-sm text-gray-600">Sentiment Score</div>
            </div>
            
            <div className="text-center">
              <div className="text-xl font-bold text-indigo-600">
                {marketSentiment.confidence_level || 'LOW'}
              </div>
              <div className="text-sm text-gray-600">Confidence Level</div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-700 font-medium">AI Recommendation:</p>
            <p className="text-sm text-gray-600">{marketSentiment.recommended_action}</p>
          </div>
        </div>
      )}

      {/* Trading Status & Controls */}
      {tradingStatus && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">⚙️ AI Trading Controller</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Trading Status</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Trading Enabled:</span>
                  <span className={`font-medium ${tradingStatus.trading_enabled ? 'text-green-600' : 'text-red-600'}`}>
                    {tradingStatus.trading_enabled ? 'YES' : 'NO'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Auto Pause:</span>
                  <span className={`font-medium ${tradingStatus.auto_pause_enabled ? 'text-green-600' : 'text-gray-600'}`}>
                    {tradingStatus.auto_pause_enabled ? 'ENABLED' : 'DISABLED'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Profit Protection:</span>
                  <span className={`font-medium ${tradingStatus.profit_protection_enabled ? 'text-green-600' : 'text-gray-600'}`}>
                    {tradingStatus.profit_protection_enabled ? 'ENABLED' : 'DISABLED'}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-3">Session Statistics</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Trades Executed:</span>
                  <span className="font-medium">{tradingStatus.session_stats?.trades_executed || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Trades Prevented:</span>
                  <span className="font-medium text-blue-600">{tradingStatus.session_stats?.trades_prevented || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Win Rate:</span>
                  <span className="font-medium text-green-600">{tradingStatus.session_stats?.win_rate?.toFixed(1) || 0}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Profit:</span>
                  <span className={`font-medium ${(tradingStatus.session_stats?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    ${tradingStatus.session_stats?.total_profit?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => controlTrading(tradingStatus.trading_enabled ? 'pause' : 'resume')}
              className={`px-4 py-2 rounded font-medium ${
                tradingStatus.trading_enabled 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-green-500 hover:bg-green-600 text-white'
              }`}
            >
              {tradingStatus.trading_enabled ? 'Pause Trading' : 'Resume Trading'}
            </button>
            
            <button
              onClick={fetchAIData}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded font-medium"
            >
              Refresh Status
            </button>
          </div>
        </div>
      )}

      {/* Safety Thresholds */}
      {tradingStatus?.safety_thresholds && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">🎯 Safety Thresholds</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Safety Score: {tradingStatus.safety_thresholds.min_safety_score}
              </label>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full" 
                  style={{width: `${tradingStatus.safety_thresholds.min_safety_score}%`}}
                ></div>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Profit Probability: {(tradingStatus.safety_thresholds.min_profit_probability * 100).toFixed(0)}%
              </label>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-600 h-2 rounded-full" 
                  style={{width: `${tradingStatus.safety_thresholds.min_profit_probability * 100}%`}}
                ></div>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Loss Probability: {(tradingStatus.safety_thresholds.max_loss_probability * 100).toFixed(0)}%
              </label>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-red-600 h-2 rounded-full" 
                  style={{width: `${tradingStatus.safety_thresholds.max_loss_probability * 100}%`}}
                ></div>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Confidence: {(tradingStatus.safety_thresholds.min_confidence * 100).toFixed(0)}%
              </label>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-600 h-2 rounded-full" 
                  style={{width: `${tradingStatus.safety_thresholds.min_confidence * 100}%`}}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AILossPreventionPanel;
