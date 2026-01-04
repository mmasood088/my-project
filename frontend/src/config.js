// API Configuration
export const API_BASE_URL = "http://20.20.20.132:8000";

export const API_ENDPOINTS = {
  signals: `${API_BASE_URL}/api/signals`,
  signalStats: `${API_BASE_URL}/api/signals/stats`,
  entries: `${API_BASE_URL}/api/entries`,
  entryStats: `${API_BASE_URL}/api/entries/stats`,
  dashboard: `${API_BASE_URL}/api/dashboard/stats`,
  recentActivity: `${API_BASE_URL}/api/dashboard/recent-activity`,
  symbols: `${API_BASE_URL}/api/symbols`,
  settings: `${API_BASE_URL}/api/settings`,
  livePrices: `${API_BASE_URL}/api/live-prices`,
  dashboardTable: `${API_BASE_URL}/api/dashboard/table`,
};
