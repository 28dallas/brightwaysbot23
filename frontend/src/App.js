import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar } from 'recharts';
import StrategyBuilder from './components/StrategyBuilder';
import EnhancedStrategyBuilder from './components/EnhancedStrategyBuilder';
import Analytics from './components/Analytics';
import AdvancedAnalytics from './components/AdvancedAnalytics';
import Notifications from './components/Notifications';
import NotificationCenter from './components/NotificationCenter';
import TradingStatus from './components/TradingStatus';
import AutoTrading from './components/AutoTrading';
import AITradingHub from './components/AITradingHub';
import AccountSettings from './components/AccountSettings';
import TradingModeToggle from './components/TradingModeToggle';
import Login from './components/Login';

function App() {
  const [price, setPrice] = useState(0);
  const [digitFreq, setDigitFreq] = useState(Array(10).fill(0));
  const [priceHistory, setPriceHistory] = useState([]);
  const [isTrading, setIsTrading] = useState(false);
  const [historicalTicks, setHistoricalTicks] = useState([]);
  const [historicalTrades, setHistoricalTrades] = useState([]);
  const [trades, setTrades] = useState([]);
  const [balance, setBalance] = useState(10000);
  const [initialBalance, setInitialBalance] = useState(10000);
  const [stakeAmount, setStakeAmount] = useState(1);
  const [user, setUser] = useState({ email: 'demo@brightbot.com', full_name: 'Demo User' });
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [strategies, setStrategies] = useState([]);
  const [aiPrediction, setAiPrediction] = useState(null);
  const [accountType, setAccountType] = useState('demo');
  const [apiToken, setApiToken] = useState('');
  const [showApiTokenModal, setShowApiTokenModal] = useState(false);
  const [selectedContract, setSelectedContract] = useState('DIGITEVEN');
  const [tradeDuration, setTradeDuration] = useState(5);
  const [barrier, setBarrier] = useState('');
  const [barrier2, setBarrier2] = useState('');
  const [multiplier, setMultiplier] = useState(1);
  const [symbol, setSymbol] = useState('R_100');

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws');

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setPrice(data.price ?? 0);

        // Update AI prediction if available
        if (data.ai_prediction) {
          setAiPrediction(data.ai_prediction);
        }

        // Update digit frequency
        setDigitFreq(prev => {
          const newFreq = [...prev];
          if (data.last_digit !== undefined && data.last_digit !== null) {
            newFreq[data.last_digit]++;
          }
          return newFreq;
        });

        // Update price history
        setPriceHistory(prev => [...prev.slice(-50), {
          time: new Date(data.timestamp).toLocaleTimeString(),
          price: data.price ?? 0,
          last_digit: data.last_digit ?? 0,
          ai_prediction: data.ai_prediction
        }]);

        // Auto trading logic
        if (isTrading && balance >= stakeAmount) {
          // Simple example: predict last digit will be even or odd randomly
          const prediction = Math.random() > 0.5 ? 1 : 0; // 1 for odd, 0 for even
          const actual = data.last_digit % 2;
          const result = prediction === actual ? 'win' : 'lose';
          const pnl = result === 'win' ? stakeAmount * 0.8 : -stakeAmount; // example payout 0.8x

          const newTrade = {
            id: trades.length + 1,
            timestamp: new Date().toISOString(),
            stake: stakeAmount,
            prediction,
            result,
            pnl
          };

          setTrades(prev => [newTrade, ...prev].slice(0, 50));
          setBalance(prev => prev + pnl);
        }
      } catch (error) {
        console.error('Error processing websocket message:', error);
      }
    };

    ws.onclose = (event) => {
      console.warn('WebSocket connection closed:', event);
      // Optionally, set some state to indicate connection closed
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      // Optionally, set some state to indicate error
    };

    return () => ws.close();
  }, [isTrading, balance, stakeAmount, trades.length]);

  // Fetch balance and historical data
  useEffect(() => {
    const checkApiTokenSetup = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        // No auth, show modal for setup (or login first, but for demo, show modal)
        setShowApiTokenModal(true);
        return;
      }

      try {
        const response = await fetch('http://localhost:8001/api/user', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const userData = await response.json();
          if (!userData.api_token_set) {
            setShowApiTokenModal(true);
          }
        } else {
          // Invalid token, clear and show modal
          localStorage.removeItem('token');
          setShowApiTokenModal(true);
        }
      } catch (error) {
        console.error('Error checking API token setup:', error);
        setShowApiTokenModal(true);
      }
    };

    checkApiTokenSetup();
    fetchData();
    fetchAIPrediction();
  }, []);
  
  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated]);

  const fetchData = async () => {
    try {
      const headers = {};
      if (apiToken) {
        headers['api_token'] = apiToken;
      }
      const accountTypeParam = accountType ? `&account_type=${accountType}` : '';
      
      const balanceResponse = await fetch(`http://localhost:8001/api/balance?${Date.now()}${accountTypeParam}`, { headers });
      if (balanceResponse.ok) {
        const balanceData = await balanceResponse.json();
        console.log('Balance data received:', balanceData);
        
        const newBalance = balanceData.balance || 10000;
        setBalance(newBalance);
        if (initialBalance === 10000) {
          setInitialBalance(newBalance);
        }
        setAccountType(balanceData.account_type || 'demo');
      } else {
        console.error('Balance API error:', balanceResponse.status);
        setBalance(10000);
        setAccountType('demo');
      }
      
      try {
        const historyResponse = await fetch('http://localhost:8001/api/history', { headers });
        if (historyResponse.ok) {
          const historyData = await historyResponse.json();
          setHistoricalTicks(historyData.ticks || []);
          setHistoricalTrades(historyData.trades || []);
        }
      } catch (historyError) {
        console.log('History fetch failed, continuing with balance only');
      }
      
    } catch (error) {
      console.error('Error fetching data:', error);
      setBalance(10000);
      setInitialBalance(10000);
      setAccountType('demo');
    }
  };

  const fetchAIPrediction = async () => {
    try {
      setAiPrediction({
        prediction: Math.floor(Math.random() * 10),
        confidence: 0.5 + Math.random() * 0.4
      });
    } catch (error) {
      console.error('Error fetching AI prediction:', error);
    }
  };


  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
    setBalance(10000);
    setTrades([]);
  };
  
  const handleLogin = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    setBalance(userData.balance);
    setInitialBalance(userData.balance);
    setAccountType(userData.account_type);
  };

  const toggleAccountType = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };

      const response = await fetch('http://localhost:8001/api/account/toggle', {
        method: 'POST',
        headers
      });

      const result = await response.json();

      if (response.ok) {
        setAccountType(result.account_type);
        setBalance(result.balance);
        setInitialBalance(result.balance);
        alert(`Switched to ${result.account_type.toUpperCase()} mode. Balance: $${result.balance}`);
        setTimeout(() => fetchData(), 1000); // Refresh after 1 second
      } else {
        alert('Failed to toggle account type: ' + (result.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error toggling account type:', error);
      alert('Error toggling account type');
    }
  };

  const saveApiToken = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8001/api/account/api-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ api_token: apiToken })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setShowApiTokenModal(false);
        setApiToken('');
        setBalance(data.balance);
        setAccountType(data.account_type);
        alert(data.message);
        fetchData();
      } else {
        alert(data.message || 'Failed to save API token');
      }
    } catch (error) {
      console.error('Error saving API token:', error);
      alert('Error saving API token');
    }
  };

  const placeTrade = async (prediction) => {
    try {
      const response = await fetch('http://localhost:8001/api/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract_type: selectedContract,
          symbol: symbol,
          amount: stakeAmount,
          duration: tradeDuration,
          duration_unit: 't',
          barrier: barrier,
          prediction: prediction
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        alert(`Trade placed! Contract ID: ${result.contract_id}`);
        fetchData(); // Refresh balance and trades
      } else {
        alert('Trade failed: ' + (result.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error placing trade:', error);
      alert('Error placing trade');
    }
  };

  const handleSaveStrategy = (strategy) => {
    const newStrategy = { ...strategy, id: Date.now() };
    setStrategies(prev => [...prev, newStrategy]);
  };

  const handleAITradeExecute = async (tradeData) => {
    try {
      // Execute trade with AI recommendations
      const result = Math.random() > 0.5 ? 'win' : 'lose';
      const pnl = result === 'win' ? tradeData.stake * 0.8 : -tradeData.stake;
      
      const newTrade = {
        id: trades.length + 1,
        timestamp: new Date().toISOString(),
        stake: tradeData.stake,
        prediction: tradeData.prediction,
        result,
        pnl,
        contract_type: tradeData.contract_type,
        ai_trade: true
      };
      
      setTrades(prev => [newTrade, ...prev]);
      setBalance(prev => prev + pnl);
      
    } catch (error) {
      console.error('Error executing AI trade:', error);
    }
  };

  const handleAISettingsCopy = (settings) => {
    // Copy AI settings to manual controls
    setSelectedContract(settings.contractType);
    setStakeAmount(settings.stake);
    setTradeDuration(settings.duration);
  };

  const freqData = digitFreq.map((freq, digit) => ({ digit, frequency: freq }));




  
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <Notifications trades={trades} balance={balance} />
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">🤖 Brightbot AI Trading</h1>
          <p className="text-gray-400">Premium AI-Powered Trading Assistant</p>
        </div>
        <div className="flex items-center space-x-4">
          {aiPrediction && (
            <div className="bg-purple-800 px-3 py-1 rounded-lg text-sm">
              🎯 Next: {aiPrediction.prediction} ({(aiPrediction.confidence * 100).toFixed(0)}%)
            </div>
          )}
          <button
            onClick={toggleAccountType}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              accountType === 'demo' ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {accountType.toUpperCase()} {accountType === 'demo' ? '📊' : '💰'}
          </button>
          <div className="text-white">
            👋 {user?.full_name || user?.email}
          </div>
          <button onClick={handleLogout} className="text-gray-400 hover:text-white">
            Reset Demo
          </button>
        </div>
      </div>
      
      <div className="flex space-x-4 mb-6 overflow-x-auto">
        {[
          { key: 'dashboard', label: '📊 Dashboard', icon: '📊' },
          { key: 'ai-hub', label: '🤖 AI Trading Hub', icon: '🤖' },
          { key: 'strategy', label: '🛠️ Strategy Builder', icon: '🛠️' },
          { key: 'analytics', label: '📈 Advanced Analytics', icon: '📈' },
          { key: 'settings', label: '⚙️ Account Settings', icon: '⚙️' },
          { key: 'notifications', label: '🔔 Notifications', icon: '🔔' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded whitespace-nowrap transition-all duration-200 ${
              activeTab === tab.key 
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg' 
                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      {activeTab === 'dashboard' && (
        <>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Live Price</h2>
          <div className="text-4xl font-mono text-green-400">{(price || 0).toFixed(5)}</div>
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Account Balance</h2>
          <div className={`text-3xl font-mono ${balance >= 1000 ? 'text-green-400' : balance >= 500 ? 'text-yellow-400' : 'text-red-400'}`}>
            ${(balance || 0).toFixed(2)}
          </div>
          <div className="text-sm text-gray-400 mt-2">
            P&L: ${((balance || 0) - (initialBalance || 0)).toFixed(2)}
          </div>
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Trading Controls</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Contract Type</label>
              <select
                value={selectedContract}
                onChange={(e) => setSelectedContract(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="DIGITEVEN">Even Digits</option>
                <option value="DIGITODD">Odd Digits</option>
                <option value="DIGITDIFF">Differs</option>
                <option value="DIGITMATCH">Matches</option>
                <option value="DIGITOVER">Over</option>
                <option value="DIGITUNDER">Under</option>
                <option value="CALL">Rise</option>
                <option value="PUT">Fall</option>
                <option value="ASIANU">Asian Up</option>
                <option value="ASIAND">Asian Down</option>
                <option value="ONETOUCH">One Touch</option>
                <option value="NOTOUCH">No Touch</option>
                <option value="RANGE">Stays Between</option>
                <option value="UPORDOWN">Goes Outside</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Stake Amount</label>
              <input
                type="number"
                min="0.1"
                max={balance}
                step="0.1"
                value={stakeAmount}
                onChange={(e) => setStakeAmount(Math.min(parseFloat(e.target.value) || 0, balance))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Symbol</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value="R_100">Volatility 100 Index</option>
                <option value="R_75">Volatility 75 Index</option>
                <option value="R_50">Volatility 50 Index</option>
                <option value="R_25">Volatility 25 Index</option>
                <option value="R_10">Volatility 10 Index</option>
                <option value="1HZ100V">Volatility 100 (1s) Index</option>
                <option value="1HZ75V">Volatility 75 (1s) Index</option>
                <option value="1HZ50V">Volatility 50 (1s) Index</option>
                <option value="1HZ25V">Volatility 25 (1s) Index</option>
                <option value="1HZ10V">Volatility 10 (1s) Index</option>
                <option value="BOOM1000">Boom 1000 Index</option>
                <option value="BOOM500">Boom 500 Index</option>
                <option value="CRASH1000">Crash 1000 Index</option>
                <option value="CRASH500">Crash 500 Index</option>
                <option value="JD10">Jump 10 Index</option>
                <option value="JD25">Jump 25 Index</option>
                <option value="JD50">Jump 50 Index</option>
                <option value="JD75">Jump 75 Index</option>
                <option value="JD100">Jump 100 Index</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Duration (ticks)</label>
              <input
                type="number"
                min="1"
                max="10"
                value={tradeDuration}
                onChange={(e) => setTradeDuration(parseInt(e.target.value) || 5)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              />
            </div>
            {(['DIGITOVER', 'DIGITUNDER', 'DIGITMATCH', 'DIGITDIFF'].includes(selectedContract)) && (
              <div>
                <label className="block text-sm font-medium mb-2">Target Digit (0-9)</label>
                <input
                  type="number"
                  min="0"
                  max="9"
                  value={barrier}
                  onChange={(e) => setBarrier(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  placeholder="Enter digit 0-9"
                />
              </div>
            )}
            {(['ONETOUCH', 'NOTOUCH', 'CALL', 'PUT'].includes(selectedContract)) && (
              <div>
                <label className="block text-sm font-medium mb-2">Barrier Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={barrier}
                  onChange={(e) => setBarrier(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  placeholder="Enter barrier price"
                />
              </div>
            )}
            {(['RANGE', 'UPORDOWN'].includes(selectedContract)) && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Lower Barrier</label>
                  <input
                    type="number"
                    step="0.01"
                    value={barrier}
                    onChange={(e) => setBarrier(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Upper Barrier</label>
                  <input
                    type="number"
                    step="0.01"
                    value={barrier2}
                    onChange={(e) => setBarrier2(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  />
                </div>
              </>
            )}
            <div className="grid grid-cols-2 gap-2">
              <button 
                onClick={() => placeTrade(0)}
                disabled={balance < stakeAmount}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded font-medium disabled:bg-gray-600"
              >
                Sell/Even
              </button>
              <button 
                onClick={() => placeTrade(1)}
                disabled={balance < stakeAmount}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded font-medium disabled:bg-gray-600"
              >
                Buy/Odd
              </button>
            </div>
            <button 
              onClick={() => setIsTrading(!isTrading)}
              disabled={balance < stakeAmount}
              className={`w-full px-6 py-2 rounded font-medium ${
                balance < stakeAmount 
                  ? 'bg-gray-600 cursor-not-allowed' 
                  : isTrading 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {balance < stakeAmount ? 'Insufficient Balance' : isTrading ? 'Stop Auto Trading' : 'Start Auto Trading'}
            </button>
          </div>
        </div>
        
        <TradingStatus />
      </div>
      
      <div className="mb-6">
        <TradingModeToggle />
      </div>
      
      <div className="mt-6">
        <AutoTrading />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Price Chart</h2>
          <LineChart width={400} height={200} data={priceHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} />
          </LineChart>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Digit Frequency</h2>
          <BarChart width={400} height={200} data={freqData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="digit" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="frequency" fill="#3b82f6" />
          </BarChart>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg overflow-auto max-h-64">
          <h2 className="text-xl font-semibold mb-4">Historical Ticks (Last 100)</h2>
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="border-b border-gray-700 px-2 py-1">ID</th>
                <th className="border-b border-gray-700 px-2 py-1">Timestamp</th>
                <th className="border-b border-gray-700 px-2 py-1">Price</th>
                <th className="border-b border-gray-700 px-2 py-1">Last Digit</th>
              </tr>
            </thead>
            <tbody>
              {historicalTicks.map(tick => (
                <tr key={tick.id}>
                  <td className="border-b border-gray-700 px-2 py-1">{tick.id}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{new Date(tick.timestamp).toLocaleString()}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{tick.price !== undefined && tick.price !== null ? tick.price.toFixed(5) : '0.00000'}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{tick.last_digit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg overflow-auto max-h-64">
          <h2 className="text-xl font-semibold mb-4">Historical Trades (Last 50)</h2>
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="border-b border-gray-700 px-2 py-1">ID</th>
                <th className="border-b border-gray-700 px-2 py-1">Timestamp</th>
                <th className="border-b border-gray-700 px-2 py-1">Stake</th>
                <th className="border-b border-gray-700 px-2 py-1">Prediction</th>
                <th className="border-b border-gray-700 px-2 py-1">Result</th>
                <th className="border-b border-gray-700 px-2 py-1">PnL</th>
              </tr>
            </thead>
            <tbody>
              {historicalTrades.map(trade => (
                <tr key={trade.id}>
                  <td className="border-b border-gray-700 px-2 py-1">{trade.id}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{new Date(trade.timestamp).toLocaleString()}</td>
              <td className="border-b border-gray-700 px-2 py-1">{trade.stake !== undefined && trade.stake !== null ? trade.stake.toFixed(2) : '0.00'}</td>
              <td className="border-b border-gray-700 px-2 py-1">{trade.prediction}</td>
              <td className="border-b border-gray-700 px-2 py-1">{trade.result}</td>
              <td className="border-b border-gray-700 px-2 py-1">{trade.pnl !== undefined && trade.pnl !== null ? trade.pnl.toFixed(2) : '0.00'}</td>
                </tr>
              ))}
              {trades.map(trade => (
                <tr key={trade.id + '-auto'}>
                  <td className="border-b border-gray-700 px-2 py-1">{trade.id}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{new Date(trade.timestamp).toLocaleString()}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{trade.stake !== undefined && trade.stake !== null ? trade.stake.toFixed(2) : '0.00'}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{trade.prediction}</td>
                  <td className="border-b border-gray-700 px-2 py-1">{trade.result}</td>
                  <td className={`border-b border-gray-700 px-2 py-1 ${trade.pnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.pnl !== undefined && trade.pnl !== null ? trade.pnl.toFixed(2) : '0.00'}
                    {trade.ai_trade && <span className="ml-1 text-xs text-blue-400">🤖</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
        </>
      )}
      
      {activeTab === 'ai-hub' && (
        <AITradingHub 
          currentPrice={price} 
          priceHistory={priceHistory}
          onTradeExecute={handleAITradeExecute}
          onSettingsCopy={handleAISettingsCopy}
        />
      )}
      
      {activeTab === 'strategy' && (
        <EnhancedStrategyBuilder onSaveStrategy={handleSaveStrategy} />
      )}
      
      {activeTab === 'analytics' && (
        <AdvancedAnalytics trades={trades} balance={balance} initialBalance={initialBalance} />
      )}
      
      {activeTab === 'settings' && (
        <AccountSettings />
      )}
      
      {activeTab === 'notifications' && (
        <NotificationCenter />
      )}
      
      {/* API Token Modal */}
      {showApiTokenModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Enter Deriv API Token</h3>
            <p className="text-gray-400 mb-4 text-sm">
              To trade with real money, you need to provide your Deriv API token.
              The system will automatically use the appropriate App ID.
            </p>
            <input
              type="password"
              placeholder="Enter your API token"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <p className="text-xs text-gray-400 mb-4">
              <a href="https://app.deriv.com/account/api-token" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                How to get API token
              </a>
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowApiTokenModal(false);
                  setApiToken('');
                }}
                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded"
              >
                Cancel
              </button>
              <button
                onClick={saveApiToken}
                disabled={!apiToken.trim()}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded disabled:bg-gray-600"
              >
                Save & Switch to Live
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
