import { useState, useEffect } from 'react';
import apiService from '../services/api';

function EntriesPage() {
  const [entries, setEntries] = useState([]);
  const [symbols, setSymbols] = useState([]); // Add this line
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('active'); // 'active', 'all'
  const [symbolFilter, setSymbolFilter] = useState('');
  const [timeframeFilter, setTimeframeFilter] = useState('');

  useEffect(() => {
    fetchData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [filter, symbolFilter, timeframeFilter]);
  // Fetch active symbols for dropdown
  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const data = await apiService.getSymbols();
        setSymbols(data.symbols || []);
      } catch (error) {
        console.error('Error fetching symbols:', error);
      }
    };
    fetchSymbols();
  }, []);
  const fetchData = async () => {
    try {
      setLoading(true);
      const [entriesData, statsData] = await Promise.all([
        apiService.getEntries({
          active_only: filter === 'active',
          symbol: symbolFilter || undefined,
          timeframe: timeframeFilter || undefined,
          limit: 100
        }),
        apiService.getEntryStats()
      ]);
      
      setEntries(entriesData.entries || []);
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching entries:', error);
    } finally {
      setLoading(false);
    }
  };

  const getValidationColor = (status) => {
    switch (status) {
      case 'VALIDATED':
        return 'bg-green-100 text-green-800';
      case 'VALIDATING':
        return 'bg-yellow-100 text-yellow-800';
      case 'INVALIDATED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getExitColor = (status) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-blue-100 text-blue-800';
      case 'EXIT-1':
        return 'bg-yellow-100 text-yellow-800';
      case 'EXIT-2':
        return 'bg-orange-100 text-orange-800';
      case 'EXIT-3':
        return 'bg-red-100 text-red-800';
      case 'EXITED':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getProfitColor = (profit) => {
    if (profit > 0) return 'text-green-600';
    if (profit < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatPrice = (price) => {
    if (!price) return '-';
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            📈 Entry Tracking
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            
            {/* Active Entries */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-blue-500 rounded-md p-3">
                  <span className="text-2xl">📊</span>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Active Entries
                    </dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {stats.active_entries}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>

            {/* Validated */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-green-500 rounded-md p-3">
                  <span className="text-2xl">✅</span>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Validated
                    </dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {stats.validated}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>

            {/* Invalidated */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-red-500 rounded-md p-3">
                  <span className="text-2xl">❌</span>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Invalidated
                    </dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {stats.invalidated}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>

            {/* Avg Profit */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-yellow-500 rounded-md p-3">
                  <span className="text-2xl">💰</span>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Avg Profit
                    </dt>
                    <dd className={`text-2xl font-semibold ${getProfitColor(stats.avg_profit_pct)}`}>
                      {stats.avg_profit_pct >= 0 ? '+' : ''}{stats.avg_profit_pct.toFixed(2)}%
                    </dd>
                  </dl>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="space-y-4">
            
            {/* Row 1: Active/All Toggle and Refresh */}
            <div className="flex items-center justify-between">
              <div className="flex space-x-2">
                <button
                  onClick={() => setFilter('active')}
                  className={`px-4 py-2 rounded-md ${
                    filter === 'active'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Active Only
                </button>
                <button
                  onClick={() => setFilter('all')}
                  className={`px-4 py-2 rounded-md ${
                    filter === 'all'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  All Entries
                </button>
              </div>

              {/* Refresh Button */}
              <button
                onClick={fetchData}
                className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition"
              >
                🔄 Refresh
              </button>
            </div>

            {/* Row 2: Symbol and Timeframe Filters */}
            <div className="flex items-center space-x-4">
              
              {/* Symbol Filter */}
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Symbol
                </label>
                <select
                  value={symbolFilter}
                  onChange={(e) => setSymbolFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Symbols</option>
                  {symbols.map(sym => (
                    <option key={sym.id} value={sym.symbol}>{sym.symbol}</option>
                  ))}
                </select>
              </div>

              {/* Timeframe Filter */}
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeframe
                </label>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setTimeframeFilter('')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm ${
                      timeframeFilter === ''
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setTimeframeFilter('15m')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm ${
                      timeframeFilter === '15m'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    15m
                  </button>
                  <button
                    onClick={() => setTimeframeFilter('1h')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm ${
                      timeframeFilter === '1h'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    1h
                  </button>
                  <button
                    onClick={() => setTimeframeFilter('4h')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm ${
                      timeframeFilter === '4h'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    4h
                  </button>
                  <button
                    onClick={() => setTimeframeFilter('1d')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm ${
                      timeframeFilter === '1d'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    1d
                  </button>
                </div>
              </div>

            </div>

          </div>
        </div>

        {/* Entries Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="text-lg">Loading entries...</div>
            </div>
          ) : entries.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-lg text-gray-500">No entries found</div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Entry Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Symbol
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Signal
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Entry Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Current Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Profit
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Validation
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Exit Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Exits Hit
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(entry.entry_datetime)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-gray-900">{entry.symbol}</div>
                        <div className="text-sm text-gray-500">{entry.timeframe}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                          {entry.entry_signal}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(entry.entry_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(entry.current_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`text-sm font-semibold ${getProfitColor(entry.current_profit_pct)}`}>
                          {entry.current_profit_pct >= 0 ? '+' : ''}{entry.current_profit_pct.toFixed(2)}%
                        </div>
                        <div className="text-xs text-gray-500">
                          Max: {entry.max_profit_pct.toFixed(2)}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getValidationColor(entry.validation_status)}`}>
                          {entry.validation_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getExitColor(entry.exit_status)}`}>
                          {entry.exit_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex space-x-1">
                          <span className={`px-2 py-1 rounded ${entry.exit_1_hit ? 'bg-red-200 text-red-800' : 'bg-gray-200 text-gray-500'}`}>
                            E1
                          </span>
                          <span className={`px-2 py-1 rounded ${entry.exit_2_hit ? 'bg-red-200 text-red-800' : 'bg-gray-200 text-gray-500'}`}>
                            E2
                          </span>
                          <span className={`px-2 py-1 rounded ${entry.exit_3_hit ? 'bg-red-200 text-red-800' : 'bg-gray-200 text-gray-500'}`}>
                            E3
                          </span>
                        </div>
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

export default EntriesPage;