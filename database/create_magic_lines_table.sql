-- ============================================
-- CREATE MAGIC_LINES TABLE
-- ============================================
-- Purpose: Store user-defined Magic Line levels (manual entry targets)
-- Used for: Signal scoring bonus, dashboard display, alerts

CREATE TABLE IF NOT EXISTS magic_lines (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    
    -- Magic Line price level
    magic_line_price DECIMAL(20, 8) NOT NULL,
    
    -- Display settings (for future chart plotting)
    line_color VARCHAR(20) DEFAULT 'purple',
    line_width INTEGER DEFAULT 2,
    line_style VARCHAR(20) DEFAULT 'Solid',  -- Solid, Dashed, Dotted
    
    -- Tracking
    active BOOLEAN DEFAULT true,
    notes TEXT,  -- User notes about why this level matters
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_magic_lines_symbol ON magic_lines(symbol);
CREATE INDEX IF NOT EXISTS idx_magic_lines_active ON magic_lines(active);

-- Comments
COMMENT ON TABLE magic_lines IS 'User-defined Magic Line price levels for each symbol';
COMMENT ON COLUMN magic_lines.magic_line_price IS 'Target price level defined by user';
COMMENT ON COLUMN magic_lines.notes IS 'User notes - why this level is important';

SELECT 'Magic Lines table created successfully!' AS status;