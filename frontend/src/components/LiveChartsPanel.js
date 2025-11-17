import React, { useState, useEffect, useRef } from 'react';
import './LiveChartsPanel.css';

const LiveChartsPanel = () => {
  const [mt5Data, setMt5Data] = useState([]);
  const [tvSignals, setTvSignals] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const tvWidgetRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    initTradingViewWidget();
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const initTradingViewWidget = () => {
    if (window.TradingView) {
      new window.TradingView.widget({
        container_id: "tradingview_chart",
        width: "100%",
        height: 400,
        symbol: "FX:EURUSD",
        interval: "1",
        timezone: "Etc/UTC",
        theme: "dark",
        style: "1",
        locale: "en",
        toolbar_bg: "#f1f3f6",
        enable_publishing: false,
        hide_top_toolbar: false,
        hide_legend: true,
        save_image: false,
        studies: ["MASimple@tv-basicstudies"],
        show_popup_button: true,
        popup_width: "1000",
        popup_height: "650"
      });
    }
  };

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8001/api/integrations/ws');
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log('Connected to integration WebSocket');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'mt5_position') {
        setMt5Data(prev => [data.data, ...prev.slice(0, 9)]);
      } else if (data.type === 'tradingview_signal') {
        setTvSignals(prev => [data.data, ...prev.slice(0, 9)]);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatPrice = (price) => {
    return parseFloat(price).toFixed(5);
  };

  return (
    <div className="live-charts-panel">
      <div className="connection-status">
        <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
        {isConnected ? 'Live Data Connected' : 'Connecting...'}
      </div>

      <div className="charts-container">
        {/* TradingView Chart */}
        <div className="chart-section">
          <h3>📈 TradingView Live Chart</h3>
          <div id="tradingview_chart"></div>
          
          <div className="signals-feed">
            <h4>Recent TradingView Signals</h4>
            <div className="signals-list">
              {tvSignals.map((signal, index) => (
                <div key={index} className="signal-item">
                  <span className="signal-time">{formatTime(signal.timestamp)}</span>
                  <span className={`signal-action ${signal.action}`}>{signal.action.toUpperCase()}</span>
                  <span className="signal-symbol">{signal.symbol}</span>
                  <span className="signal-price">{formatPrice(signal.price)}</span>
                  <span className="signal-strategy">{signal.strategy}</span>
                </div>
              ))}
              {tvSignals.length === 0 && (
                <div className="no-data">No TradingView signals yet</div>
              )}
            </div>
          </div>
        </div>

        {/* MT5 Data */}
        <div className="chart-section">
          <h3>🔧 MetaTrader 5 Live Data</h3>
          
          <div className="mt5-positions">
            <h4>Open Positions</h4>
            <div className="positions-list">
              {mt5Data.map((position, index) => (
                <div key={index} className="position-item">
                  <div className="position-header">
                    <span className="position-time">{formatTime(position.time)}</span>
                    <span className={`position-type ${position.type}`}>
                      {position.type.toUpperCase()}
                    </span>
                  </div>
                  <div className="position-details">
                    <span className="position-symbol">{position.symbol}</span>
                    <span className="position-volume">Vol: {position.volume}</span>
                    <span className="position-price">Price: {formatPrice(position.price_open)}</span>
                    <span className={`position-profit ${position.profit >= 0 ? 'positive' : 'negative'}`}>
                      P&L: ${position.profit.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
              {mt5Data.length === 0 && (
                <div className="no-data">No MT5 positions yet</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Live Activity Feed */}
      <div className="activity-feed">
        <h3>🔴 Live Activity Feed</h3>
        <div className="activity-list">
          {[...tvSignals.map(s => ({...s, source: 'TradingView'})), 
            ...mt5Data.map(p => ({...p, source: 'MT5'}))]
            .sort((a, b) => new Date(b.timestamp || b.time) - new Date(a.timestamp || a.time))
            .slice(0, 10)
            .map((item, index) => (
              <div key={index} className={`activity-item ${item.source.toLowerCase()}`}>
                <span className="activity-time">
                  {formatTime(item.timestamp || item.time)}
                </span>
                <span className="activity-source">{item.source}</span>
                <span className="activity-details">
                  {item.source === 'TradingView' 
                    ? `${item.action} ${item.symbol} @ ${formatPrice(item.price)}`
                    : `${item.type} ${item.symbol} Vol:${item.volume}`
                  }
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default LiveChartsPanel;