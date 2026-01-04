-- ============================================
-- ADD BOLLINGER BANDS COLUMNS TO INDICATORS TABLE
-- ============================================

-- Add BB Basis (middle line)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_basis DECIMAL(20, 8);

-- Add Upper Bands (1σ, 2σ, 3σ)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_upper_1 DECIMAL(20, 8);

ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_upper_2 DECIMAL(20, 8);

ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_upper_3 DECIMAL(20, 8);

-- Add Lower Bands (1σ, 2σ, 3σ)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_lower_1 DECIMAL(20, 8);

ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_lower_2 DECIMAL(20, 8);

ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_lower_3 DECIMAL(20, 8);

-- Add BB Squeeze (boolean)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_squeeze BOOLEAN;

-- Add BB Position (text)
ALTER TABLE indicators 
ADD COLUMN IF NOT EXISTS bb_position VARCHAR(10);

-- Create index for BB queries (optional but improves performance)
CREATE INDEX IF NOT EXISTS idx_indicators_bb_squeeze 
ON indicators(bb_squeeze) 
WHERE bb_squeeze = true;

-- Success message
SELECT 'Bollinger Bands columns added successfully!' AS status;