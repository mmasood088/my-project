import { useState, useEffect } from 'react';
import apiService from '../services/api';

function SettingsPage() {
  const [systemInfo, setSystemInfo] = useState(null);
  const [thresholds, setThresholds] = useState(null);
  const [logs, setLogs] = useState(null);
  const [srSettings, setSRSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('system'); // system, thresholds, logs, indicators

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sysInfo, thresh, srData] = await Promise.all([
        apiService.getSystemInfo(),
        apiService.getThresholds(),
        apiService.getSRSettings()
      ]);
      
      setSystemInfo(sysInfo);
      setThresholds(thresh);
      setSRSettings(srData.settings);
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const logsData = await apiService.getLogs();
      setLogs(logsData);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            ⚙️ Settings & Configuration
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('system')}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
                  activeTab === 'system'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                System Status
              </button>
              <button
                onClick={() => setActiveTab('thresholds')}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
                  activeTab === 'thresholds'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Thresholds
              </button>
              <button
                onClick={() => {
                  setActiveTab('logs');
                  if (!logs) fetchLogs();
                }}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
                  activeTab === 'logs'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Automation Logs
              </button>
              <button
                onClick={() => setActiveTab('indicators')}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
                  activeTab === 'indicators'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Indicators
              </button>
            </nav>
          </div>
        </div>

        {/* System Status Tab */}
        {activeTab === 'system' && systemInfo && (
          <div className="space-y-6">
            
            {/* Automation Status */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Automation Status</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1 flex items-center">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
                      systemInfo.automation.enabled
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {systemInfo.automation.enabled ? '✓ Enabled' : '✗ Disabled'}
                    </span>
                  </dd>
                </div>

                <div>
                  <dt className="text-sm font-medium text-gray-500">Interval</dt>
                  <dd className="mt-1 text-lg font-semibold text-gray-900">
                    {systemInfo.automation.interval}
                  </dd>
                </div>

                <div>
                  <dt className="text-sm font-medium text-gray-500">Last Run</dt>
                  <dd className="mt-1 text-lg font-semibold text-gray-900">
                    {formatDate(systemInfo.automation.last_run)}
                  </dd>
                </div>
              </div>
            </div>

            {/* Database Statistics */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Database Statistics</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="text-center">
                  <dt className="text-sm font-medium text-gray-500">Total Candles</dt>
                  <dd className="mt-2 text-3xl font-bold text-blue-600">
                    {systemInfo.database.total_candles.toLocaleString()}
                  </dd>
                </div>

                <div className="text-center">
                  <dt className="text-sm font-medium text-gray-500">Total Signals</dt>
                  <dd className="mt-2 text-3xl font-bold text-purple-600">
                    {systemInfo.database.total_signals.toLocaleString()}
                  </dd>
                </div>

                <div className="text-center">
                  <dt className="text-sm font-medium text-gray-500">Total Entries</dt>
                  <dd className="mt-2 text-3xl font-bold text-green-600">
                    {systemInfo.database.total_entries.toLocaleString()}
                  </dd>
                </div>

                <div className="text-center">
                  <dt className="text-sm font-medium text-gray-500">Active Symbols</dt>
                  <dd className="mt-2 text-3xl font-bold text-orange-600">
                    {systemInfo.database.active_symbols}
                  </dd>
                </div>
              </div>
            </div>

            {/* API Information */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">API Information</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Version</dt>
                  <dd className="mt-1 text-lg font-semibold text-gray-900">
                    {systemInfo.api.version}
                  </dd>
                </div>

                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-green-100 text-green-800">
                      ✓ Running
                    </span>
                  </dd>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Thresholds Tab */}
        {activeTab === 'thresholds' && thresholds && (
          <div className="space-y-6">
            
            {/* Signal Thresholds */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Signal Thresholds</h2>
              <p className="text-sm text-gray-500 mb-4">
                Minimum score required to generate each signal type
              </p>
              
              <div className="space-y-4">
                {Object.entries(thresholds.signal_thresholds).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between py-3 border-b border-gray-200 last:border-0">
                    <div>
                      <dt className="text-sm font-medium text-gray-700 uppercase">
                        {key.replace('_', '-')}
                      </dt>
                    </div>
                    <dd className="text-2xl font-bold text-gray-900">
                      {value}
                    </dd>
                  </div>
                ))}
              </div>
            </div>

            {/* Entry Validation */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Entry Validation Settings</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-green-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-green-700 mb-2">Validation Threshold</dt>
                  <dd className="text-3xl font-bold text-green-600">
                    +{thresholds.entry_validation.validation_profit}%
                  </dd>
                  <p className="text-xs text-green-600 mt-1">Profit required to validate entry</p>
                </div>

                <div className="bg-red-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-red-700 mb-2">Invalidation Threshold</dt>
                  <dd className="text-3xl font-bold text-red-600">
                    {thresholds.entry_validation.invalidation_loss}%
                  </dd>
                  <p className="text-xs text-red-600 mt-1">Loss that triggers invalidation</p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-blue-700 mb-2">Intraday Stop</dt>
                  <dd className="text-2xl font-bold text-blue-600">
                    {thresholds.entry_validation.intraday_stop_multiplier}x ATR
                  </dd>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-blue-700 mb-2">Intraday Target</dt>
                  <dd className="text-2xl font-bold text-blue-600">
                    {thresholds.entry_validation.intraday_target_multiplier}x ATR
                  </dd>
                </div>

                <div className="bg-purple-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-purple-700 mb-2">Swing Stop</dt>
                  <dd className="text-2xl font-bold text-purple-600">
                    {thresholds.entry_validation.swing_stop_multiplier}x ATR
                  </dd>
                </div>

                <div className="bg-purple-50 p-4 rounded-lg">
                  <dt className="text-sm font-medium text-purple-700 mb-2">Swing Target</dt>
                  <dd className="text-2xl font-bold text-purple-600">
                    {thresholds.entry_validation.swing_target_multiplier}x ATR
                  </dd>
                </div>
              </div>
            </div>

            {/* Exit Zones */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Exit Zones</h2>
              <p className="text-sm text-gray-500 mb-4">
                Percentage of target price for each exit level
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-yellow-50 p-4 rounded-lg text-center">
                  <dt className="text-sm font-medium text-yellow-700 mb-2">EXIT-1</dt>
                  <dd className="text-3xl font-bold text-yellow-600">
                    {thresholds.exit_zones.exit_1_pct}%
                  </dd>
                  <p className="text-xs text-yellow-600 mt-1">of target</p>
                </div>

                <div className="bg-orange-50 p-4 rounded-lg text-center">
                  <dt className="text-sm font-medium text-orange-700 mb-2">EXIT-2</dt>
                  <dd className="text-3xl font-bold text-orange-600">
                    {thresholds.exit_zones.exit_2_pct}%
                  </dd>
                  <p className="text-xs text-orange-600 mt-1">of target</p>
                </div>

                <div className="bg-red-50 p-4 rounded-lg text-center">
                  <dt className="text-sm font-medium text-red-700 mb-2">EXIT-3</dt>
                  <dd className="text-3xl font-bold text-red-600">
                    {thresholds.exit_zones.exit_3_pct}%
                  </dd>
                  <p className="text-xs text-red-600 mt-1">of target (full)</p>
                </div>
              </div>
            </div>

            {/* Note */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> {thresholds.note}
              </p>
            </div>

          </div>
        )}

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Automation Logs</h2>
              <button
                onClick={fetchLogs}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition text-sm"
              >
                🔄 Refresh Logs
              </button>
            </div>

            {logs ? (
              <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                <pre className="text-xs whitespace-pre-wrap font-mono">
                  {logs.logs}
                </pre>
                {logs.showing_lines && (
                  <p className="text-xs text-gray-400 mt-4">
                    Showing last {logs.showing_lines} lines of {logs.total_lines} total lines
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Click "Refresh Logs" to view automation logs</p>
              </div>
            )}
          </div>
        )}

        {/* Indicators Tab */}
        {activeTab === 'indicators' && srSettings && (
          <div className="space-y-6">
            
            {/* S/R Settings */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Support & Resistance Settings</h2>
              <p className="text-sm text-gray-500 mb-6">
                Configure support and resistance levels for each symbol. Auto mode uses 30-day high/low.
              </p>

              <div className="space-y-6">
                {srSettings.map((setting) => (
                  <SRSettingCard
                    key={setting.symbol}
                    setting={setting}
                    onUpdate={async (updatedSetting) => {
                      try {
                        const result = await apiService.updateSRSettings(updatedSetting);
                        if (result.success) {
                          // Refresh S/R settings
                          const srData = await apiService.getSRSettings();
                          setSRSettings(srData.settings);
                          alert(`✓ Updated S/R for ${updatedSetting.symbol}`);
                        } else {
                          alert(`✗ Error: ${result.message}`);
                        }
                      } catch (error) {
                        console.error('Error updating S/R:', error);
                        alert('✗ Failed to update S/R settings');
                      }
                    }}
                  />
                ))}
              </div>

              {/* Recalculate Button */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <button
                  onClick={async () => {
                    if (confirm('Recalculate auto S/R for all symbols?')) {
                      try {
                        const result = await apiService.recalculateSR();
                        if (result.success) {
                          const srData = await apiService.getSRSettings();
                          setSRSettings(srData.settings);
                          alert(`✓ ${result.message}`);
                        }
                      } catch (error) {
                        alert('✗ Failed to recalculate S/R');
                      }
                    }
                  }}
                  className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition"
                >
                  🔄 Recalculate All Auto S/R
                </button>
              </div>
            </div>

          </div>
        )}

      </main>
    </div>
  );
}

// ==================== S/R SETTING CARD COMPONENT ====================
function SRSettingCard({ setting, onUpdate }) {
  const [mode, setMode] = useState(setting.mode);
  const [manualSupport, setManualSupport] = useState(setting.manual_support);
  const [manualResistance, setManualResistance] = useState(setting.manual_resistance);
  const [hasChanges, setHasChanges] = useState(false);

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setHasChanges(true);
  };

  const handleSupportChange = (value) => {
    setManualSupport(parseFloat(value) || 0);
    setHasChanges(true);
  };

  const handleResistanceChange = (value) => {
    setManualResistance(parseFloat(value) || 0);
    setHasChanges(true);
  };

  const handleSave = () => {
    onUpdate({
      symbol: setting.symbol,
      mode: mode,
      manual_support: mode === 'manual' ? manualSupport : 0,
      manual_resistance: mode === 'manual' ? manualResistance : 0
    });
    setHasChanges(false);
  };

  return (
    <div className="border border-gray-200 rounded-lg p-6 bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{setting.symbol}</h3>
        {hasChanges && (
          <span className="text-xs text-orange-600 font-medium">● Unsaved changes</span>
        )}
      </div>

      {/* Mode Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">Mode</label>
        <div className="flex space-x-4">
          <button
            onClick={() => handleModeChange('auto')}
            className={`flex-1 px-4 py-2 rounded-md font-medium transition ${
              mode === 'auto'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Auto
          </button>
          <button
            onClick={() => handleModeChange('manual')}
            className={`flex-1 px-4 py-2 rounded-md font-medium transition ${
              mode === 'manual'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Manual
          </button>
        </div>
      </div>

      {/* Support & Resistance Values */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Support */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Support {mode === 'auto' && <span className="text-xs text-gray-500">(auto-calculated)</span>}
          </label>
          {mode === 'auto' ? (
            <div className="px-4 py-2 bg-white border border-gray-300 rounded-md text-gray-900 font-semibold">
              {setting.auto_support.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          ) : (
            <input
              type="number"
              step="0.01"
              value={manualSupport}
              onChange={(e) => handleSupportChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter support level"
            />
          )}
        </div>

        {/* Resistance */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Resistance {mode === 'auto' && <span className="text-xs text-gray-500">(auto-calculated)</span>}
          </label>
          {mode === 'auto' ? (
            <div className="px-4 py-2 bg-white border border-gray-300 rounded-md text-gray-900 font-semibold">
              {setting.auto_resistance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          ) : (
            <input
              type="number"
              step="0.01"
              value={manualResistance}
              onChange={(e) => handleResistanceChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter resistance level"
            />
          )}
        </div>
      </div>

      {/* Save Button */}
      {hasChanges && (
        <button
          onClick={handleSave}
          className="w-full px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition font-medium"
        >
          Save Changes
        </button>
      )}
    </div>
  );
}

export default SettingsPage;