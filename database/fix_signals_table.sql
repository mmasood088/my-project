-- ============================================
-- FIX SIGNALS TABLE - Remove Old Columns
-- ============================================
-- Drop old columns that conflict with new structure

ALTER TABLE signals DROP COLUMN IF EXISTS score CASCADE;
ALTER TABLE signals DROP COLUMN IF EXISTS timeframe_type CASCADE;

-- Make sure these columns allow NULL (since not all signals have entry/stop/target)
ALTER TABLE signals ALTER COLUMN entry_price DROP NOT NULL;
ALTER TABLE signals ALTER COLUMN stop_loss DROP NOT NULL;
ALTER TABLE signals ALTER COLUMN target_price DROP NOT NULL;

SELECT 'Signals table fixed successfully!' AS status;