-- ============================================
-- ADD VOLUME ANALYSIS COLUMNS TO INDICATORS TABLE
-- ============================================

-- Add Volume Average (20-period SMA of volume)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS volume_avg DECIMAL(20, 8);

-- Add Volume Signal (H = High, N = Normal, L = Low)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS volume_signal VARCHAR(1);

-- Create index for volume queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_volume_signal 
ON indicators(volume_signal) 
WHERE volume_signal IN ('H', 'L');

-- Success message
SELECT 'Volume columns added successfully!' AS status;