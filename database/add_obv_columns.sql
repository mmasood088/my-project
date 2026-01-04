-- ============================================
-- ADD OBV COLUMNS TO INDICATORS TABLE
-- ============================================

-- Add OBV (On-Balance Volume - cumulative volume flow)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS obv DECIMAL(20, 2);

-- Add OBV-MA (Moving average of OBV - smoothed trend)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS obv_ma DECIMAL(20, 2);

-- Create index for OBV queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_obv 
ON indicators(obv);

-- Success message
SELECT 'OBV columns added successfully!' AS status;