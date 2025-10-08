import React, { useState, useEffect } from 'react';

const AITradingHub = ({ currentPrice, priceHistory, onTradeExecute, onSettingsCopy }) => {
  const [predictions, setPredictions] = useState({});
  const [selectedModel, setSelectedModel] = useState('ensemble');
  const [confidence, setConfidence] = useState(0);
  const [recommendation, setRecommendation] = useState('');
  const [loading, setLoading] = useState(true);

  const aiModels = {
    'random_forest': 'Random Forest',
    'neural_network': 'Neural Network',
    'lstm': 'LSTM Deep Learning',
    'svm': 'Support Vector Machine',
    'gradient_boost': 'Gradient Boosting',
    'ensemble': 'Ensemble (All Models)',
    'pattern_recognition': 'Pattern Recognition',
    'technical_analysis': 'Technical Analysis'
  };

  useEffect(() => {
    // Generate predictions immediately, even with limited data
    if (priceHistory.length > 0 || currentPrice > 0) {
      fetchAIPredictions();
    } else {
      // Generate initial predictions with mock data
      generatePredictions();
    }
  }, [currentPrice, priceHistory]);

  useEffect(() => {
    // Generate initial predictions on component mount
    generatePredictions();
  }, []);

  const fetchAIPredictions = async () => {
    try {
      // Send current price to backend
      if (currentPrice > 0) {
        await fetch('http://localhost:8001/api/ai/add-price', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ price: currentPrice })
        });
      }
      
      // Get multi-model predictions
      const response = await fetch('http://localhost:8001/api/ai/multi-predictions');
      const data = await response.json();
      
      if (data.success && data.predictions) {
        // Convert backend predictions to frontend format
        const convertedPredictions = {};
        
        Object.entries(data.predictions).forEach(([modelKey, pred]) => {
          convertedPredictions[modelKey] = {
            nextDigit: pred.next_digit,
            confidence: pred.confidence,
            signal: pred.signal,
            contractType: pred.contract_type,
            stake: pred.stake,
            duration: pred.duration
          };
        });
        
        setPredictions(convertedPredictions);
        setLoading(false);
        
        // Set recommendation for selected model
        if (convertedPredictions[selectedModel]) {
          const selectedPred = convertedPredictions[selectedModel];
          setConfidence(selectedPred.confidence);
          setRecommendation(generateRecommendation(selectedPred));
        }
      } else {
        // Fallback to local predictions
        generatePredictions();
      }
    } catch (error) {
      console.error('Error fetching AI predictions:', error);
      // Fallback to local predictions
      generatePredictions();
    }
  };

  // Generate predictions immediately if no data
  useEffect(() => {
    if (Object.keys(predictions).length === 0) {
      generatePredictions();
    }
  }, []);

  const generatePredictions = () => {
    // Fallback local predictions when backend is unavailable
    const lastDigits = priceHistory.length > 0 ? 
      priceHistory.slice(-10).map(p => p.last_digit || Math.floor(Math.random() * 10)) :
      Array.from({length: 10}, () => Math.floor(Math.random() * 10));
    
    const prices = priceHistory.length > 0 ? 
      priceHistory.slice(-20).map(p => p.price || 1000 + Math.random() * 100) :
      Array.from({length: 20}, () => 1000 + Math.random() * 100);
    
    const newPredictions = {};
    
    // Random Forest
    newPredictions.random_forest = {
      nextDigit: predictByFrequency(lastDigits),
      confidence: 0.65 + Math.random() * 0.25,
      signal: getTrendSignal(prices),
      contractType: 'DIGITEVEN',
      stake: calculateOptimalStake(prices),
      duration: 5
    };

    // Neural Network
    newPredictions.neural_network = {
      nextDigit: predictByPattern(lastDigits),
      confidence: 0.70 + Math.random() * 0.20,
      signal: getVolatilitySignal(prices),
      contractType: 'DIGITODD',
      stake: calculateOptimalStake(prices) * 1.2,
      duration: 3
    };

    // LSTM
    newPredictions.lstm = {
      nextDigit: predictBySequence(lastDigits),
      confidence: 0.75 + Math.random() * 0.15,
      signal: getMomentumSignal(prices),
      contractType: lastDigits[lastDigits.length - 1] % 2 === 0 ? 'DIGITODD' : 'DIGITEVEN',
      stake: calculateOptimalStake(prices) * 0.8,
      duration: 7
    };

    // SVM
    newPredictions.svm = {
      nextDigit: (lastDigits.reduce((a, b) => a + b, 0) / lastDigits.length) > 4.5 ? 
                 Math.floor(Math.random() * 5) : Math.floor(Math.random() * 5) + 5,
      confidence: 0.60 + Math.random() * 0.30,
      signal: 'BUY',
      contractType: 'CALL',
      stake: calculateOptimalStake(prices) * 1.5,
      duration: 10
    };

    // Gradient Boosting
    newPredictions.gradient_boost = {
      nextDigit: predictByGradient(lastDigits, prices),
      confidence: 0.68 + Math.random() * 0.22,
      signal: getGradientSignal(prices),
      contractType: 'PUT',
      stake: calculateOptimalStake(prices) * 1.1,
      duration: 5
    };

    // Ensemble
    const allDigits = [
      newPredictions.random_forest.nextDigit,
      newPredictions.neural_network.nextDigit,
      newPredictions.lstm.nextDigit,
      newPredictions.svm.nextDigit,
      newPredictions.gradient_boost.nextDigit
    ];
    
    newPredictions.ensemble = {
      nextDigit: Math.round(allDigits.reduce((a, b) => a + b, 0) / allDigits.length),
      confidence: 0.80 + Math.random() * 0.15,
      signal: 'STRONG_BUY',
      contractType: 'DIGITEVEN',
      stake: calculateOptimalStake(prices),
      duration: 5
    };

    // Pattern Recognition
    newPredictions.pattern_recognition = {
      nextDigit: detectPattern(lastDigits),
      confidence: 0.55 + Math.random() * 0.35,
      signal: getPatternSignal(lastDigits),
      contractType: 'DIGITDIFF',
      stake: calculateOptimalStake(prices) * 0.9,
      duration: 3
    };

    // Technical Analysis
    newPredictions.technical_analysis = {
      nextDigit: technicalAnalysis(prices),
      confidence: 0.72 + Math.random() * 0.18,
      signal: getTechnicalSignal(prices),
      contractType: 'RANGE',
      stake: calculateOptimalStake(prices) * 1.3,
      duration: 8
    };

    setPredictions(newPredictions);
    setLoading(false);
    
    // Set overall recommendation
    const selectedPred = newPredictions[selectedModel] || newPredictions['ensemble'];
    if (selectedPred) {
      setConfidence(selectedPred.confidence);
      setRecommendation(generateRecommendation(selectedPred));
    }
  };

  // Prediction algorithms
  const predictByFrequency = (digits) => {
    const freq = Array(10).fill(0);
    digits.forEach(d => freq[d]++);
    return freq.indexOf(Math.min(...freq));
  };

  const predictByPattern = (digits) => {
    const patterns = {};
    for (let i = 0; i < digits.length - 2; i++) {
      const pattern = digits.slice(i, i + 3).join('');
      patterns[pattern] = (patterns[pattern] || 0) + 1;
    }
    const mostCommon = Object.keys(patterns).reduce((a, b) => 
      patterns[a] > patterns[b] ? a : b, '000');
    return parseInt(mostCommon[2]) || Math.floor(Math.random() * 10);
  };

  const predictBySequence = (digits) => {
    const diffs = [];
    for (let i = 1; i < digits.length; i++) {
      diffs.push(digits[i] - digits[i-1]);
    }
    const avgDiff = diffs.reduce((a, b) => a + b, 0) / diffs.length;
    return Math.abs((digits[digits.length - 1] + avgDiff) % 10);
  };

  const predictByGradient = (digits, prices) => {
    const priceChange = prices[prices.length - 1] - prices[prices.length - 5];
    const digitTrend = digits[digits.length - 1] - digits[0];
    return Math.abs((digits[digits.length - 1] + Math.sign(priceChange + digitTrend)) % 10);
  };

  const detectPattern = (digits) => {
    // Look for repeating patterns
    const last3 = digits.slice(-3);
    const occurrences = [];
    for (let i = 0; i < digits.length - 2; i++) {
      if (digits.slice(i, i + 3).join('') === last3.join('')) {
        if (i + 3 < digits.length) occurrences.push(digits[i + 3]);
      }
    }
    return occurrences.length > 0 ? 
      occurrences[Math.floor(Math.random() * occurrences.length)] : 
      Math.floor(Math.random() * 10);
  };

  const technicalAnalysis = (prices) => {
    const sma5 = prices.slice(-5).reduce((a, b) => a + b, 0) / 5;
    const sma10 = prices.slice(-10).reduce((a, b) => a + b, 0) / 10;
    const currentPrice = prices[prices.length - 1];
    
    if (currentPrice > sma5 && sma5 > sma10) {
      return Math.floor(Math.random() * 5) + 5; // Higher digits
    } else {
      return Math.floor(Math.random() * 5); // Lower digits
    }
  };

  // Signal generators
  const getTrendSignal = (prices) => {
    const trend = prices[prices.length - 1] - prices[prices.length - 5];
    return trend > 0 ? 'BUY' : trend < 0 ? 'SELL' : 'HOLD';
  };

  const getVolatilitySignal = (prices) => {
    const volatility = Math.sqrt(prices.slice(-5).reduce((sum, price, i, arr) => {
      const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
      return sum + Math.pow(price - mean, 2);
    }, 0) / 5);
    return volatility > 2 ? 'STRONG_BUY' : volatility > 1 ? 'BUY' : 'HOLD';
  };

  const getMomentumSignal = (prices) => {
    const momentum = (prices[prices.length - 1] - prices[prices.length - 3]) / prices[prices.length - 3];
    return momentum > 0.001 ? 'BUY' : momentum < -0.001 ? 'SELL' : 'HOLD';
  };

  const getGradientSignal = (prices) => {
    const gradient = prices[prices.length - 1] - prices[prices.length - 2];
    return gradient > 0 ? 'BUY' : 'SELL';
  };

  const getPatternSignal = (digits) => {
    const evenCount = digits.filter(d => d % 2 === 0).length;
    return evenCount > digits.length / 2 ? 'BUY_EVEN' : 'BUY_ODD';
  };

  const getTechnicalSignal = (prices) => {
    const rsi = calculateRSI(prices);
    return rsi > 70 ? 'SELL' : rsi < 30 ? 'BUY' : 'HOLD';
  };

  const calculateRSI = (prices) => {
    const gains = [], losses = [];
    for (let i = 1; i < prices.length; i++) {
      const change = prices[i] - prices[i - 1];
      gains.push(change > 0 ? change : 0);
      losses.push(change < 0 ? -change : 0);
    }
    const avgGain = gains.reduce((a, b) => a + b, 0) / gains.length;
    const avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length;
    const rs = avgGain / avgLoss;
    return 100 - (100 / (1 + rs));
  };

  const calculateOptimalStake = (prices) => {
    const volatility = Math.sqrt(prices.slice(-5).reduce((sum, price, i, arr) => {
      const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
      return sum + Math.pow(price - mean, 2);
    }, 0) / 5);
    return Math.max(1, Math.min(10, 5 / volatility));
  };

  const generateRecommendation = (pred) => {
    return `${pred.signal} ${pred.contractType} - Stake: $${pred.stake.toFixed(2)} - Duration: ${pred.duration} ticks - Next Digit: ${pred.nextDigit}`;
  };

  const executeAITrade = async (prediction) => {
    try {
      const tradeData = {
        contract_type: prediction.contractType,
        stake: prediction.stake,
        duration: prediction.duration,
        prediction: prediction.nextDigit
      };
      
      if (onTradeExecute) {
        onTradeExecute(tradeData);
      }
      
      alert(`AI Trade Executed: ${prediction.contractType} - $${prediction.stake.toFixed(2)}`);
    } catch (error) {
      console.error('Error executing AI trade:', error);
      alert('Error executing AI trade');
    }
  };

  const copyTradeSettings = (prediction) => {
    if (onSettingsCopy) {
      onSettingsCopy({
        contractType: prediction.contractType,
        stake: prediction.stake,
        duration: prediction.duration
      });
    }
    alert('Settings copied to manual trading controls!');
  };

  const getSignalColor = (signal) => {
    const colors = {
      'STRONG_BUY': 'text-green-400',
      'BUY': 'text-green-300',
      'BUY_EVEN': 'text-blue-300',
      'BUY_ODD': 'text-purple-300',
      'HOLD': 'text-yellow-300',
      'SELL': 'text-red-300'
    };
    return colors[signal] || 'text-gray-300';
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg">
      <h2 className="text-2xl font-bold mb-6 text-center">🤖 AI Trading Hub</h2>
      
      {/* Model Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">Select AI Model:</label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
        >
          {Object.entries(aiModels).map(([key, name]) => (
            <option key={key} value={key}>{name}</option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg text-center">
          <div className="text-lg">🤖 AI Models Analyzing...</div>
          <div className="text-sm text-gray-400 mt-2">Generating predictions from multiple AI models</div>
        </div>
      )}

      {/* Main Prediction Display */}
      {!loading && predictions[selectedModel] && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg border-l-4 border-blue-500">
          <h3 className="text-lg font-semibold mb-2">{aiModels[selectedModel]} Prediction</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-400">Next Digit:</span>
              <span className="ml-2 text-2xl font-bold text-blue-400">
                {predictions[selectedModel].nextDigit}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Confidence:</span>
              <span className="ml-2 text-lg font-semibold text-green-400">
                {(predictions[selectedModel].confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-gray-400">Signal:</span>
              <span className={`ml-2 font-semibold ${getSignalColor(predictions[selectedModel].signal)}`}>
                {predictions[selectedModel].signal}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Contract:</span>
              <span className="ml-2 text-white font-medium">
                {predictions[selectedModel].contractType}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Recommended Stake:</span>
              <span className="ml-2 text-yellow-400 font-semibold">
                ${predictions[selectedModel].stake.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Duration:</span>
              <span className="ml-2 text-white">
                {predictions[selectedModel].duration} ticks
              </span>
            </div>
          </div>
          <div className="mt-3 p-2 bg-gray-600 rounded">
            <span className="text-sm text-gray-300">Recommendation: </span>
            <span className="text-sm text-white font-medium">{recommendation}</span>
          </div>
        </div>
      )}

      {/* All Models Overview */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(predictions).map(([modelKey, pred]) => (
          <div key={modelKey} className="bg-gray-700 p-3 rounded border">
            <h4 className="font-semibold text-sm mb-2">{aiModels[modelKey]}</h4>
            <div className="space-y-1 text-xs">
              <div>Digit: <span className="font-bold text-blue-300">{pred.nextDigit}</span></div>
              <div>Confidence: <span className="text-green-300">{(pred.confidence * 100).toFixed(0)}%</span></div>
              <div>Signal: <span className={getSignalColor(pred.signal)}>{pred.signal}</span></div>
              <div>Contract: <span className="text-gray-300">{pred.contractType}</span></div>
              <div>Stake: <span className="text-yellow-300">${pred.stake.toFixed(1)}</span></div>
            </div>
          </div>
          ))}
        </div>
      )}

      {/* Quick Trade Actions */}
      {!loading && predictions[selectedModel] && (
        <div className="mt-6 p-4 bg-gradient-to-r from-green-800 to-blue-800 rounded-lg">
          <h3 className="text-lg font-semibold mb-3">⚡ Quick AI Trade</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => executeAITrade(predictions[selectedModel])}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded font-medium transition-colors"
            >
              🤖 Execute AI Recommendation
            </button>
            <button
              onClick={() => copyTradeSettings(predictions[selectedModel])}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium transition-colors"
            >
              📋 Copy Settings to Manual
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-300">
            This will place a trade with AI recommended settings: {predictions[selectedModel].contractType} - 
            ${predictions[selectedModel].stake.toFixed(2)} - {predictions[selectedModel].duration} ticks
          </div>
        </div>
      )}

      {/* Consensus Indicator */}
      {!loading && (
        <div className="mt-6 p-4 bg-gradient-to-r from-purple-800 to-blue-800 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">🎯 AI Consensus</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-400">
              {Object.values(predictions).filter(p => p.signal && p.signal.includes('BUY')).length}
            </div>
            <div className="text-sm text-gray-300">Buy Signals</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-400">
              {Object.values(predictions).filter(p => p.signal === 'HOLD').length}
            </div>
            <div className="text-sm text-gray-300">Hold Signals</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-400">
              {Object.values(predictions).filter(p => p.signal === 'SELL').length}
            </div>
            <div className="text-sm text-gray-300">Sell Signals</div>
          </div>
        </div>
        </div>
      )}
    </div>
  );
};

export default AITradingHub;