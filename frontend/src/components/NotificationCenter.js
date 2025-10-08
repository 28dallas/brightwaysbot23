import React, { useState, useEffect } from 'react';

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);
  const [settings, setSettings] = useState({
    email: true,
    push: true,
    telegram: false,
    whatsapp: false,
    trade_alerts: true,
    balance_alerts: true,
    strategy_alerts: true
  });

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/api/notifications', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setNotifications(data.notifications || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'trade': return '💰';
      case 'balance': return '💳';
      case 'strategy': return '🎯';
      case 'system': return '⚙️';
      case 'warning': return '⚠️';
      default: return '📢';
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case 'trade': return 'border-green-500';
      case 'balance': return 'border-blue-500';
      case 'strategy': return 'border-purple-500';
      case 'system': return 'border-gray-500';
      case 'warning': return 'border-yellow-500';
      default: return 'border-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* Notification Settings */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold text-white mb-4">🔔 Notification Settings</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-white font-semibold mb-3">Delivery Methods</h3>
            <div className="space-y-3">
              {[
                { key: 'email', label: 'Email Notifications', icon: '📧' },
                { key: 'push', label: 'Push Notifications', icon: '📱' },
                { key: 'telegram', label: 'Telegram Bot', icon: '📲' },
                { key: 'whatsapp', label: 'WhatsApp', icon: '💬' }
              ].map(method => (
                <label key={method.key} className="flex items-center space-x-3 text-white">
                  <input
                    type="checkbox"
                    checked={settings[method.key]}
                    onChange={(e) => setSettings({...settings, [method.key]: e.target.checked})}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <span>{method.icon} {method.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-3">Alert Types</h3>
            <div className="space-y-3">
              {[
                { key: 'trade_alerts', label: 'Trade Execution Alerts', icon: '💰' },
                { key: 'balance_alerts', label: 'Balance & P&L Alerts', icon: '💳' },
                { key: 'strategy_alerts', label: 'Strategy Performance', icon: '🎯' }
              ].map(alert => (
                <label key={alert.key} className="flex items-center space-x-3 text-white">
                  <input
                    type="checkbox"
                    checked={settings[alert.key]}
                    onChange={(e) => setSettings({...settings, [alert.key]: e.target.checked})}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                  />
                  <span>{alert.icon} {alert.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6">
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium">
            Save Settings
          </button>
        </div>
      </div>

      {/* Recent Notifications */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold text-white mb-4">📬 Recent Notifications</h2>
        
        {notifications.length > 0 ? (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`bg-gray-700 p-4 rounded-lg border-l-4 ${getNotificationColor(notification.type)} ${
                  !notification.is_read ? 'bg-opacity-80' : 'bg-opacity-40'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <span className="text-2xl">{getNotificationIcon(notification.type)}</span>
                    <div>
                      <p className="text-white font-medium">{notification.message}</p>
                      <p className="text-gray-400 text-sm mt-1">
                        {new Date(notification.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  {!notification.is_read && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="text-6xl mb-4">🔕</div>
            <p className="text-gray-400">No notifications yet</p>
            <p className="text-gray-500 text-sm">You'll see trade alerts and system updates here</p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold text-white mb-4">⚡ Quick Actions</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg text-left">
            <div className="text-2xl mb-2">📧</div>
            <div className="font-semibold">Test Email</div>
            <div className="text-sm opacity-80">Send test notification</div>
          </button>
          
          <button className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-lg text-left">
            <div className="text-2xl mb-2">🔗</div>
            <div className="font-semibold">Connect Telegram</div>
            <div className="text-sm opacity-80">Link your Telegram bot</div>
          </button>
          
          <button className="bg-purple-600 hover:bg-purple-700 text-white p-4 rounded-lg text-left">
            <div className="text-2xl mb-2">📱</div>
            <div className="font-semibold">Enable Push</div>
            <div className="text-sm opacity-80">Allow browser notifications</div>
          </button>
        </div>
      </div>

      {/* Integration Setup */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold text-white mb-4">🔗 Integration Setup</h2>
        
        <div className="space-y-4">
          <div className="bg-gray-700 p-4 rounded-lg">
            <h3 className="text-white font-semibold mb-2">📲 Telegram Bot Setup</h3>
            <p className="text-gray-400 text-sm mb-3">
              1. Search for @BrightbotTrading_bot on Telegram<br/>
              2. Start the bot and get your chat ID<br/>
              3. Enter your chat ID below
            </p>
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="Your Telegram Chat ID"
                className="flex-1 p-2 bg-gray-600 text-white rounded border border-gray-500"
              />
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
                Connect
              </button>
            </div>
          </div>

          <div className="bg-gray-700 p-4 rounded-lg">
            <h3 className="text-white font-semibold mb-2">💬 WhatsApp Integration</h3>
            <p className="text-gray-400 text-sm mb-3">
              Get trade alerts directly on WhatsApp (Premium feature)
            </p>
            <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
              Upgrade to Premium
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}