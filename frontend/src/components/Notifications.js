import React, { useState, useEffect } from 'react';

export default function Notifications({ trades, balance }) {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (trades.length > 0) {
      const lastTrade = trades[0];
      const newNotification = {
        id: Date.now(),
        type: lastTrade.result === 'win' ? 'success' : 'error',
        message: `Trade ${lastTrade.result.toUpperCase()}: ${lastTrade.result === 'win' ? '+' : ''}$${lastTrade.pnl.toFixed(2)}`,
        timestamp: new Date()
      };
      
      setNotifications(prev => [newNotification, ...prev.slice(0, 4)]);
      
      // Auto remove after 5 seconds
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== newNotification.id));
      }, 5000);
    }
  }, [trades]);

  return (
    <div className="fixed top-4 right-4 space-y-2 z-50">
      {notifications.map(notification => (
        <div
          key={notification.id}
          className={`p-4 rounded-lg shadow-lg max-w-sm ${
            notification.type === 'success' 
              ? 'bg-green-600 text-white' 
              : 'bg-red-600 text-white'
          }`}
        >
          <div className="font-medium">{notification.message}</div>
          <div className="text-sm opacity-75">
            {notification.timestamp.toLocaleTimeString()}
          </div>
        </div>
      ))}
    </div>
  );
}