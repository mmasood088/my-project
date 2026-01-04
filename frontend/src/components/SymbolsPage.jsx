import { useState, useEffect } from 'react';
import apiService from '../services/api';

function SymbolsPage() {
  const [symbols, setSymbols] = useState([]);
  const [symbolStatuses, setSymbolStatuses] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSymbol, setEditingSymbol] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    symbol: '',
    exchange: 'binance',
    timeframes: ['15m', '1h', '4h', '1d'],
    notes: ''
  });

  useEffect(() => {
    fetchSymbols();
  }, []);

  // Poll for status updates every 10 seconds for downloading symbols
  useEffect(() => {
    const downloadingSymbols = symbols.filter(s => 
      symbolStatuses[s.id]?.status === 'downloading'
    );

    if (downloadingSymbols.length > 0) {
      const interval = setInterval(() => {
        downloadingSymbols.forEach(symbol => {
          fetchSymbolStatus(symbol.id);
        });
      }, 10000); // Poll every 10 seconds

      return () => clearInterval(interval);
    }
  }, [symbols, symbolStatuses]);

  const fetchSymbols = async () => {
    try {
      setLoading(true);
      const data = await apiService.getSymbols();
      setSymbols(data.symbols || []);
      
      // Fetch status for each symbol
      (data.symbols || []).forEach(symbol => {
        fetchSymbolStatus(symbol.id);
      });
    } catch (error) {
      console.error('Error fetching symbols:', error);
      alert('Failed to load symbols');
    } finally {
      setLoading(false);
    }
  };

  const fetchSymbolStatus = async (symbolId) => {
    try {
      const response = await fetch(`http://20.20.20.132:8000/api/symbols/${symbolId}/status`);
      const status = await response.json();
      
      setSymbolStatuses(prev => ({
        ...prev,
        [symbolId]: status
      }));
    } catch (error) {
      console.error(`Error fetching status for symbol ${symbolId}:`, error);
    }
  };

  const handleAddSymbol = async (e) => {
    e.preventDefault();
    
    if (!formData.symbol) {
      alert('Please enter a symbol');
      return;
    }

    if (formData.timeframes.length === 0) {
      alert('Please select at least one timeframe');
      return;
    }

    try {
      const result = await apiService.addSymbol({
        symbol: formData.symbol.toUpperCase(),
        exchange: formData.exchange,
        timeframes: formData.timeframes,
        notes: formData.notes
      });

      alert(`Symbol added successfully! ${result.message}`);
      
      // Reset form
      setFormData({
        symbol: '',
        exchange: 'binance',
        timeframes: ['15m', '1h', '4h', '1d'],
        notes: ''
      });
      setShowAddForm(false);
      
      // Refresh list
      fetchSymbols();
    } catch (error) {
      console.error('Error adding symbol:', error);
      alert(error.response?.data?.detail || 'Failed to add symbol');
    }
  };

  const handleToggleTimeframe = (tf) => {
    setFormData(prev => ({
      ...prev,
      timeframes: prev.timeframes.includes(tf)
        ? prev.timeframes.filter(t => t !== tf)
        : [...prev.timeframes, tf]
    }));
  };

  const handleDeleteSymbol = async (symbolId, symbolName) => {
    if (!confirm(`Are you sure you want to remove ${symbolName}? This will stop tracking this symbol.`)) {
      return;
    }

    try {
      await fetch(`http://20.20.20.132:8000/api/symbols/${symbolId}`, {
        method: 'DELETE'
      });
      
      alert('Symbol removed successfully!');
      fetchSymbols();
    } catch (error) {
      console.error('Error deleting symbol:', error);
      alert('Failed to delete symbol');
    }
  };

  const startEdit = (symbol) => {
    setEditingSymbol(symbol.id);
    setFormData({
      symbol: symbol.symbol,
      exchange: symbol.exchange,
      timeframes: symbol.timeframes,
      notes: symbol.notes || ''
    });
  };

  const cancelEdit = () => {
    setEditingSymbol(null);
    setFormData({
      symbol: '',
      exchange: 'binance',
      timeframes: ['15m', '1h', '4h', '1d'],
      notes: ''
    });
  };

  const saveEdit = async (symbolId) => {
    if (formData.timeframes.length === 0) {
      alert('Please select at least one timeframe');
      return;
    }

    try {
      await fetch(`http://20.20.20.132:8000/api/symbols/${symbolId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeframes: formData.timeframes,
          notes: formData.notes
        })
      });

      alert('Symbol updated successfully!');
      setEditingSymbol(null);
      fetchSymbols();
    } catch (error) {
      console.error('Error updating symbol:', error);
      alert('Failed to update symbol');
    }
  };

  const getStatusBadge = (symbolId) => {
    const status = symbolStatuses[symbolId];
    
    if (!status) {
      return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">Checking...</span>;
    }

    const statusConfig = {
      'ready': { bg: 'bg-green-100', text: 'text-green-800', label: '✓ Ready' },
      'downloading': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '⏳ Downloading...' },
      'pending': { bg: 'bg-blue-100', text: 'blue-800', label: '⏸ Pending' },
      'error': { bg: 'bg-red-100', text: 'text-red-800', label: '✗ Error' },
      'partial': { bg: 'bg-orange-100', text: 'text-orange-800', label: '⚠ Partial' }
    };

    const config = statusConfig[status.status] || statusConfig['pending'];

    return (
      <span className={`px-2 py-1 text-xs ${config.bg} ${config.text} rounded font-medium`}>
        {config.label}
      </span>
    );
  };

  const getCandlesSummary = (symbolId) => {
    const status = symbolStatuses[symbolId];
    
    if (!status || !status.candles || status.candles.length === 0) {
      return <span className="text-xs text-gray-400">No data</span>;
    }

    return (
      <div className="text-xs text-gray-600">
        {status.candles.map(c => (
          <div key={c.timeframe}>
            {c.timeframe}: {c.count.toLocaleString()} candles
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">
            🎯 Symbol Management
          </h1>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition"
          >
            {showAddForm ? '✕ Cancel' : '+ Add Symbol'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        
        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">How it works</h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>When you add a new symbol:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>System checks if 6 months of historical data exists</li>
                  <li>If missing, automatically downloads data in background</li>
                  <li>Status updates automatically (refresh not needed)</li>
                  <li>Once "Ready", the symbol appears in your dashboard</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Add Symbol Form */}
        {showAddForm && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add New Symbol</h2>
            
            <form onSubmit={handleAddSymbol}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Symbol Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Symbol *
                  </label>
                  <input
                    type="text"
                    value={formData.symbol}
                    onChange={(e) => setFormData({...formData, symbol: e.target.value})}
                    placeholder="e.g., DOGE/USDT"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Format: BASE/QUOTE (e.g., BTC/USDT)</p>
                </div>

                {/* Exchange Select */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Exchange
                  </label>
                  <select
                    value={formData.exchange}
                    onChange={(e) => setFormData({...formData, exchange: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="binance">Binance</option>
                  </select>
                </div>

                {/* Timeframes */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timeframes *
                  </label>
                  <div className="flex space-x-4">
                    {['15m', '1h', '4h', '1d'].map(tf => (
                      <label key={tf} className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.timeframes.includes(tf)}
                          onChange={() => handleToggleTimeframe(tf)}
                          className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{tf}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Notes */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notes (Optional)
                  </label>
                  <input
                    type="text"
                    value={formData.notes}
                    onChange={(e) => setFormData({...formData, notes: e.target.value})}
                    placeholder="e.g., Added for swing trading"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

              </div>

              <div className="mt-6 flex space-x-4">
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition"
                >
                  Add Symbol
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Symbols Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="text-lg">Loading symbols...</div>
            </div>
          ) : symbols.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-lg text-gray-500">No symbols found</div>
              <button
                onClick={() => setShowAddForm(true)}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition"
              >
                Add Your First Symbol
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Symbol
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Exchange
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data Summary
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timeframes
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Notes
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {symbols.map((symbol) => (
                    <tr key={symbol.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-gray-900">{symbol.symbol}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {symbol.exchange}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(symbol.id)}
                      </td>
                      <td className="px-6 py-4">
                        {getCandlesSummary(symbol.id)}
                      </td>
                      <td className="px-6 py-4">
                        {editingSymbol === symbol.id ? (
                          <div className="flex space-x-2">
                            {['15m', '1h', '4h', '1d'].map(tf => (
                              <label key={tf} className="flex items-center space-x-1 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.timeframes.includes(tf)}
                                  onChange={() => handleToggleTimeframe(tf)}
                                  className="w-4 h-4 text-blue-600 rounded"
                                />
                                <span className="text-xs">{tf}</span>
                              </label>
                            ))}
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {symbol.timeframes.map(tf => (
                              <span key={tf} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                {tf}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {editingSymbol === symbol.id ? (
                          <input
                            type="text"
                            value={formData.notes}
                            onChange={(e) => setFormData({...formData, notes: e.target.value})}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                          />
                        ) : (
                          symbol.notes || '-'
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {editingSymbol === symbol.id ? (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => saveEdit(symbol.id)}
                              className="text-green-600 hover:text-green-900"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="text-gray-600 hover:text-gray-900"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => startEdit(symbol)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteSymbol(symbol.id, symbol.symbol)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </main>
    </div>
  );
}

export default SymbolsPage;