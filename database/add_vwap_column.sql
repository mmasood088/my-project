-- ============================================
-- ADD VWAP COLUMN TO INDICATORS TABLE
-- ============================================

-- Add VWAP (Volume Weighted Average Price)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS vwap DECIMAL(20, 8);

-- Create index for VWAP queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_vwap 
ON indicators(vwap);

-- Success message
SELECT 'VWAP column added successfully!' AS status;