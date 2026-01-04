-- ============================================
-- CREATE SETTINGS TABLE
-- ============================================
-- Purpose: Store system configuration and user preferences
-- Used for: Auto S/R mode, thresholds, dashboard preferences

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string',  -- string, integer, float, boolean
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT INTO settings (setting_key, setting_value, setting_type, description) VALUES
    ('auto_sr_mode', 'Enabled', 'string', 'Auto S/R (Previous Month High/Low): Enabled or Disabled'),
    ('price_action_bonus_points', '2.0', 'float', 'Bonus points for S/R breakout or Magic Line proximity'),
    
    -- Intraday thresholds (max 36)
    ('intraday_aggressive_buy_threshold', '29.0', 'float', 'Intraday A-BUY threshold'),
    ('intraday_buy_threshold', '23.0', 'float', 'Intraday BUY threshold'),
    ('intraday_early_buy_threshold', '18.0', 'float', 'Intraday EARLY-BUY threshold'),
    ('intraday_watch_threshold', '13.0', 'float', 'Intraday WATCH threshold'),
    ('intraday_caution_threshold', '9.0', 'float', 'Intraday CAUTION threshold'),
    
    -- Swing thresholds (max 41)
    ('swing_aggressive_buy_threshold', '33.0', 'float', 'Swing A-BUY threshold'),
    ('swing_buy_threshold', '26.0', 'float', 'Swing BUY threshold'),
    ('swing_early_buy_threshold', '21.0', 'float', 'Swing EARLY-BUY threshold'),
    ('swing_watch_threshold', '15.0', 'float', 'Swing WATCH threshold'),
    ('swing_caution_threshold', '10.0', 'float', 'Swing CAUTION threshold')
ON CONFLICT (setting_key) DO NOTHING;

-- Index
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key);

-- Comments
COMMENT ON TABLE settings IS 'System configuration and user preferences';

SELECT 'Settings table created successfully!' AS status;