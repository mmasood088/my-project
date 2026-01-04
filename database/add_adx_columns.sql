-- ============================================
-- ADD ADX COLUMNS TO INDICATORS TABLE
-- ============================================

-- Add ADX (Average Directional Index - trend strength)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS adx DECIMAL(20, 8);

-- Add DI+ (Directional Indicator Plus - bullish strength)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS di_plus DECIMAL(20, 8);

-- Add DI- (Directional Indicator Minus - bearish strength)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS di_minus DECIMAL(20, 8);

-- Create index for ADX queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_adx 
ON indicators(adx) 
WHERE adx > 25;

-- Success message
SELECT 'ADX columns added successfully!' AS status;