import { useState, useEffect } from "react";
import apiService from "../services/api";
import DashboardTable from "./DashboardTable";
function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentSignals, setRecentSignals] = useState([]);
  const [recentEntries, setRecentEntries] = useState([]);
  const [livePrices, setLivePrices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 30 seconds for live prices
    const interval = setInterval(() => {
      fetchDashboardData();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      console.log("Fetching dashboard data...");

      const [statsData, signalsData, entriesData, pricesData] = await Promise.all([
        apiService.getDashboardStats(),
        apiService.getSignals({ limit: 5 }),
        apiService.getEntries({ active_only: true, limit: 5 }),
        apiService.getLivePrices(),
      ]);

      console.log("Stats:", statsData);
      console.log("Signals:", signalsData);
      console.log("Entries:", entriesData);
      console.log("Live Prices:", pricesData);

      setStats(statsData);
      setRecentSignals(signalsData.signals || []);
      setRecentEntries(entriesData.entries || []);
      
      // Fix: pricesData.prices might be the array directly
      const prices = pricesData.prices || pricesData || [];
      console.log("Setting prices:", prices);
      setLivePrices(prices);
      
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      setLoading(false);
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getSignalColor = (signal) => {
    const colors = {
      "A-BUY": "bg-green-600",
      BUY: "bg-green-500",
      "EARLY-BUY": "bg-yellow-500",
      WATCH: "bg-yellow-400",
      CAUTION: "bg-orange-500",
      SELL: "bg-red-500",
    };
    return colors[signal] || "bg-gray-500";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Last Update Info */}
      {lastUpdate && (
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-800">Dashboard Overview</h2>
          <div className="text-sm text-gray-500">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Entries */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500 uppercase">
            Active Entries
          </div>
          <div className="mt-2 text-3xl font-bold text-blue-600">
            {stats?.active_entries || 0}
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500 uppercase">
            Win Rate
          </div>
          <div className="mt-2 text-3xl font-bold text-green-600">
            {stats?.win_rate || 0}%
          </div>
        </div>

        {/* Avg Profit */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500 uppercase">
            Avg Profit
          </div>
          <div className="mt-2 text-3xl font-bold text-purple-600">
            {stats?.avg_profit || 0}%
          </div>
        </div>

        {/* Signals (7d) */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500 uppercase">
            Signals (7 Days)
          </div>
          <div className="mt-2 text-3xl font-bold text-orange-600">
            {stats?.signals_last_7_days || 0}
          </div>
        </div>
      </div>

      {/* Live Prices Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">
            Live Prices 📊
          </h3>
        </div>
        <div className="p-6">
          {livePrices.length === 0 ? (
            <p className="text-gray-500 text-center py-4">Loading live prices...</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {livePrices.map((item) => (
                <div key={item.symbol} className="border border-gray-200 rounded-lg p-4">
                  <div className="text-xs text-gray-500 font-medium mb-1">
                    {item.symbol}
                  </div>
                  <div className="text-lg font-bold text-gray-900">
                    ${item.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    24h: ${item.low_24h.toFixed(2)} - ${item.high_24h.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      
      {/* Refresh Button */}
      <div className="flex justify-center">
        <button
          onClick={fetchDashboardData}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
        >
          🔄 Refresh Dashboard
        </button>
      </div>

      {/* Comprehensive Dashboard Table */}
      <div className="mt-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          📊 Complete Analysis Table
        </h2>
        <DashboardTable />
      </div>
    </div>
  );
}

export default Dashboard;