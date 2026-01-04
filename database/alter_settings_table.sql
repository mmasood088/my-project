-- ============================================
-- ALTER SETTINGS TABLE - ADD MISSING COLUMN
-- ============================================

-- Add setting_type column
ALTER TABLE settings ADD COLUMN IF NOT EXISTS setting_type VARCHAR(20) DEFAULT 'string';

-- Update existing rows to have setting_type
UPDATE settings 
SET setting_type = CASE
    WHEN setting_key LIKE '%threshold%' OR setting_key LIKE '%score%' OR setting_key LIKE '%bonus%' THEN 'float'
    WHEN setting_key LIKE '%length%' OR setting_key LIKE '%period%' THEN 'integer'
    WHEN setting_key LIKE '%enabled%' OR setting_key LIKE '%mode%' THEN 'boolean'
    ELSE 'string'
END
WHERE setting_type IS NULL OR setting_type = 'string';

-- Insert new settings if they don't exist (for Phase 2)
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

-- Comment
COMMENT ON COLUMN settings.setting_type IS 'Data type: string, integer, float, boolean';

SELECT 'Settings table altered successfully! Current settings count: ' || 
       (SELECT count(*) FROM settings) AS status;