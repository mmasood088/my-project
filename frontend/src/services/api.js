// API Service - Handles all backend communication
import axios from "axios";
import { API_BASE_URL, API_ENDPOINTS } from "../config";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // Change from 10000 to 30000 (30 seconds)
  headers: {
    "Content-Type": "application/json",
  },
});

// API Service Object
const apiService = {
  // Get signals with optional filters
  getSignals: async (params = {}) => {
    try {
      const response = await api.get(API_ENDPOINTS.signals, { params });
      return response.data;
    } catch (error) {
      console.error("Error fetching signals:", error);
      throw error;
    }
  },

  // Get signal statistics
  getSignalStats: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.signalStats);
      return response.data;
    } catch (error) {
      console.error("Error fetching signal stats:", error);
      throw error;
    }
  },

  // Get entries with optional filters
  getEntries: async (params = {}) => {
    try {
      const response = await api.get(API_ENDPOINTS.entries, { params });
      return response.data;
    } catch (error) {
      console.error("Error fetching entries:", error);
      throw error;
    }
  },

  // Get entry statistics
  getEntryStats: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.entryStats);
      return response.data;
    } catch (error) {
      console.error("Error fetching entry stats:", error);
      throw error;
    }
  },

  // Get dashboard statistics
  getDashboardStats: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.dashboard);
      return response.data;
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
      throw error;
    }
  },

  // Get recent activity
  getRecentActivity: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.recentActivity);
      return response.data;
    } catch (error) {
      console.error("Error fetching recent activity:", error);
      throw error;
    }
  },

  // Get symbols
  getSymbols: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.symbols);
      return response.data;
    } catch (error) {
      console.error("Error fetching symbols:", error);
      throw error;
    }
  },

  // Add symbol
  addSymbol: async (symbolData) => {
    try {
      const response = await api.post(API_ENDPOINTS.symbols, symbolData);
      return response.data;
    } catch (error) {
      console.error("Error adding symbol:", error);
      throw error;
    }
  },

  // ==================== NEW METHODS FOR SETTINGS ====================

  // Get system information
  getSystemInfo: async () => {
    try {
      const response = await api.get(`${API_ENDPOINTS.settings}/system`);
      return response.data;
    } catch (error) {
      console.error("Error fetching system info:", error);
      throw error;
    }
  },

  // Get thresholds
  getThresholds: async () => {
    try {
      const response = await api.get(`${API_ENDPOINTS.settings}/thresholds`);
      return response.data;
    } catch (error) {
      console.error("Error fetching thresholds:", error);
      throw error;
    }
  },

  // Get logs
  getLogs: async () => {
    try {
      const response = await api.get(`${API_ENDPOINTS.settings}/logs`);
      return response.data;
    } catch (error) {
      console.error("Error fetching logs:", error);
      throw error;
    }
  },
  // ==================== NEW METHODS FOR LIVE PRICES ====================

  // Get live prices for all active symbols
  getLivePrices: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.livePrices);
      return response.data;
    } catch (error) {
      console.error("Error fetching live prices:", error);
      throw error;
    }
  },

  // Get live price for single symbol
  getLivePrice: async (symbol) => {
    try {
      // Replace / with - for URL
      const urlSymbol = symbol.replace("/", "-");
      const response = await api.get(
        `${API_ENDPOINTS.livePrices}/${urlSymbol}`
      );
      return response.data;
    } catch (error) {
      console.error("Error fetching live price:", error);
      throw error;
    }
  },
  // Get comprehensive dashboard table
  getDashboardTable: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.dashboardTable);
      return response.data;
    } catch (error) {
      console.error("Error fetching dashboard table:", error);
      throw error;
    }
  },
  // Get comprehensive dashboard table
  getDashboardTable: async () => {
    try {
      const response = await api.get(API_ENDPOINTS.dashboardTable);
      return response.data;
    } catch (error) {
      console.error("Error fetching dashboard table:", error);
      throw error;
    }
  },

  // ==================== S/R SETTINGS ====================

  // Get S/R settings for all symbols
  getSRSettings: async () => {
    try {
      const response = await api.get(
        `${API_ENDPOINTS.settings}/support-resistance`
      );
      return response.data;
    } catch (error) {
      console.error("Error fetching S/R settings:", error);
      throw error;
    }
  },

  // Update S/R settings for a symbol
  updateSRSettings: async (data) => {
    try {
      const response = await api.put(
        `${API_ENDPOINTS.settings}/support-resistance`,
        data
      );
      return response.data;
    } catch (error) {
      console.error("Error updating S/R settings:", error);
      throw error;
    }
  },

  // Recalculate all S/R
  recalculateSR: async () => {
    try {
      const response = await api.post(
        `${API_ENDPOINTS.settings}/support-resistance/recalculate`
      );
      return response.data;
    } catch (error) {
      console.error("Error recalculating S/R:", error);
      throw error;
    }
  },
};

export default apiService;
