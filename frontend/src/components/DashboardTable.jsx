import { useState, useEffect } from "react";
import apiService from "../services/api";

function DashboardTable() {
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    symbol: "all",
    timeframe: "all",
    signal: "all",
  });

  useEffect(() => {
    fetchTableData();

    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchTableData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchTableData = async () => {
    try {
      console.log("Fetching dashboard table data...");
      const data = await apiService.getDashboardTable();
      console.log("Dashboard table response:", data);
      console.log("Rows:", data.rows);
      console.log("Row count:", data.rows?.length);
      setTableData(data.rows || []);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching table data:", error);
      setLoading(false);
    }
  };

  // Filter data
  const filteredData = tableData.filter((row) => {
    if (filters.symbol !== "all" && row.symbol !== filters.symbol) return false;
    if (filters.timeframe !== "all" && row.timeframe !== filters.timeframe)
      return false;
    if (filters.signal !== "all" && row.signal !== filters.signal) return false;
    return true;
  });

  // Get unique values for filters
  const symbols = [...new Set(tableData.map((r) => r.symbol))];
  const timeframes = [...new Set(tableData.map((r) => r.timeframe))];
  const signals = [...new Set(tableData.map((r) => r.signal).filter(Boolean))];

  // Helper functions for colors
  const getSignalColor = (signal) => {
    const colors = {
      "A-BUY": "bg-green-700 text-white",
      "BUY": "bg-green-600 text-white",
      "EARLY-BUY": "bg-yellow-500 text-white",
      "WATCH": "bg-yellow-400 text-gray-900",
      "CAUTION": "bg-orange-500 text-white",
      "SELL": "bg-red-600 text-white",
    };
    return colors[signal] || "bg-gray-500 text-white";
  };

  const getStatusColor = (status) => {
    const colors = {
      "VALIDATING": "bg-yellow-400 text-gray-900",
      "VALIDATED": "bg-green-600 text-white",
      "VALID": "bg-green-600 text-white",
      "ACTIVE": "bg-blue-600 text-white",
      "EXIT-1": "bg-orange-500 text-white",
      "EXIT-2": "bg-orange-600 text-white",
      "EXIT-3": "bg-red-600 text-white",
      "INVALIDATED": "bg-red-600 text-white",
    };
    return colors[status] || "bg-gray-500 text-white";
  };

  const getRSIColor = (rsi) => {
    if (rsi >= 70) return "bg-red-100 text-red-900";
    if (rsi <= 30) return "bg-green-100 text-green-900";
    return "bg-gray-100 text-gray-900";
  };

  const getEMAColor = (ema) => {
    if (ema === "↑↑↑") return "bg-green-100 text-green-900";
    if (ema === "↓↓↓") return "bg-red-100 text-red-900";
    return "bg-gray-100 text-gray-900";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-600">Loading dashboard table...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Symbol Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Symbol
            </label>
            <select
              value={filters.symbol}
              onChange={(e) =>
                setFilters({ ...filters, symbol: e.target.value })
              }
              className="w-full border border-gray-300 rounded px-3 py-2"
            >
              <option value="all">All Symbols</option>
              {symbols.map((sym) => (
                <option key={sym} value={sym}>
                  {sym}
                </option>
              ))}
            </select>
          </div>

          {/* Timeframe Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Timeframe
            </label>
            <div className="flex gap-2">
              {["all", "15m", "1h", "4h", "1d"].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setFilters({ ...filters, timeframe: tf })}
                  className={`px-3 py-2 rounded text-sm font-medium ${
                    filters.timeframe === tf
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  {tf === "all" ? "All" : tf}
                </button>
              ))}
            </div>
          </div>

          {/* Signal Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Signal
            </label>
            <select
              value={filters.signal}
              onChange={(e) =>
                setFilters({ ...filters, signal: e.target.value })
              }
              className="w-full border border-gray-300 rounded px-3 py-2"
            >
              <option value="all">All Signals</option>
              {signals.map((sig) => (
                <option key={sig} value={sig}>
                  {sig}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <div className="flex items-end">
            <button
              onClick={fetchTableData}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-blue-900">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                TF
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Type
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Price
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                S/R
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                ML
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                VWAP
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                VOL
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                ATR%
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                RSI
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                RSI X
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                MACD
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                MACD X
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                ADX
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                DI
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                OBV
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                EMA
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                ST1
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                ST2
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                BB
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Score
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Signal
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                E-Status
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Exit
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                Entry
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredData.length === 0 ? (
              <tr>
                <td
                  colSpan="25"
                  className="px-6 py-4 text-center text-gray-500"
                >
                  No data available
                </td>
              </tr>
            ) : (
              filteredData.map((row, idx) => (
                <tr
                  key={idx}
                  className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                >
                  {/* Symbol */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                    {row.symbol}
                  </td>

                  {/* Timeframe */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                    {row.timeframe}
                  </td>

                  {/* Type */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.tf_type === "Intraday"
                          ? "bg-orange-100 text-orange-800"
                          : "bg-purple-100 text-purple-800"
                      }`}
                    >
                      {row.tf_type === "Intraday" ? "ITD" : "SWG"}
                    </span>
                  </td>

                  {/* Current Price */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-semibold text-blue-600">
                    ${row.current_price.toFixed(2)}
                  </td>

                  {/* S/R */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-700">
                    {row.support || row.resistance ? (
                      <div>
                        {row.support && <div>S: {row.support.toFixed(2)}</div>}
                        {row.resistance && (
                          <div>R: {row.resistance.toFixed(2)}</div>
                        )}
                      </div>
                    ) : (
                      "─"
                    )}
                  </td>

                  {/* Magic Line */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700">
                    {row.magic_line ? row.magic_line.toFixed(2) : "─"}
                  </td>

                  {/* VWAP */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded font-semibold ${
                        row.vwap === "+"
                          ? "bg-green-100 text-green-800"
                          : row.vwap === "-"
                          ? "bg-red-100 text-red-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.vwap}
                    </span>
                  </td>

                  {/* Volume */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded font-semibold ${
                        row.volume === "H"
                          ? "bg-green-100 text-green-800"
                          : row.volume === "L"
                          ? "bg-red-100 text-red-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.volume}
                    </span>
                  </td>

                  {/* ATR % */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700">
                    {row.atr_pct.toFixed(2)}%
                  </td>

                  {/* RSI */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded ${getRSIColor(row.rsi)}`}>
                      {row.rsi.toFixed(1)}
                    </span>
                  </td>

                  {/* RSI Cross */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.rsi_cross === "↑"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {row.rsi_cross}
                    </span>
                  </td>

                  {/* MACD */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.macd === "+"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {row.macd}
                    </span>
                  </td>

                  {/* MACD Cross */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.macd_cross === "↑"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {row.macd_cross}
                    </span>
                  </td>

                  {/* ADX */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.adx >= 25
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.adx.toFixed(1)}
                    </span>
                  </td>

                  {/* DI */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.di === "+"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {row.di}
                    </span>
                  </td>

                  {/* OBV */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.obv === "+"
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {row.obv}
                    </span>
                  </td>

                  {/* EMA Stack */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded ${getEMAColor(row.ema_stack)}`}>
                      {row.ema_stack}
                    </span>
                  </td>

                  {/* ST1 */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.st1 === "UP"
                          ? "bg-green-100 text-green-800"
                          : row.st1 === "DN"
                          ? "bg-red-100 text-red-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.st1 === "UP" ? "↑" : row.st1 === "DN" ? "↓" : "─"}
                    </span>
                  </td>

                  {/* ST2 */}
                  <td className="px-3 py-2 whitespace-nowrap text-center text-sm">
                    <span
                      className={`px-2 py-1 rounded ${
                        row.st2 === "UP"
                          ? "bg-green-100 text-green-800"
                          : row.st2 === "DN"
                          ? "bg-red-100 text-red-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.st2 === "UP" ? "↑" : row.st2 === "DN" ? "↓" : "─"}
                    </span>
                  </td>

                  {/* BB Position */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-700">
                    {row.bb_position || "─"}
                    {row.bb_squeeze && " 🔥"}
                  </td>

                  {/* Score */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm font-semibold text-gray-900">
                    {row.score.toFixed(1)}
                  </td>

                  {/* Signal */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs">
                    {row.signal ? (
                      <span
                        className={`px-2 py-1 rounded font-bold ${getSignalColor(
                          row.signal
                        )}`}
                      >
                        {row.signal}
                      </span>
                    ) : (
                      "─"
                    )}
                  </td>

                  {/* Entry Status */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs">
                    {row.entry_status && row.entry_status !== "─" ? (
                      <span
                        className={`px-2 py-1 rounded font-bold ${getStatusColor(
                          row.entry_status
                        )}`}
                      >
                        {row.entry_status}
                      </span>
                    ) : (
                      "─"
                    )}
                  </td>

                  {/* Exit Reason */}
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-700">
                    {row.exit_reason && row.exit_reason !== "─"
                      ? row.exit_reason
                      : "─"}
                  </td>

                  {/* Entry Price */}
                  <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                    {row.entry_price ? `$${row.entry_price.toFixed(2)}` : "─"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="text-sm text-gray-600 text-center">
        Showing {filteredData.length} of {tableData.length} rows
      </div>
    </div>
  );
}

export default DashboardTable;