"""
Magic Line Manager
User-Defined Price Levels (Manual Entry Targets)

Features:
- Manual price level input
- Bulk import from formatted string
- Price comparison logic
"""

import re
from sqlalchemy import text
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

class MagicLineManager:
    """
    Manage user-defined Magic Line price levels
    
    Magic Line = Manual price target/alert level set by user
    Used for: Entry signals, alerts, dashboard display
    """
    
    def __init__(self):
        self.engine = engine
    
    def set_magic_line(self, symbol: str, price: float, notes: str = "", 
                       line_color: str = 'purple', line_width: int = 2, 
                       line_style: str = 'Solid', active: bool = True):
        """
        Set Magic Line for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            price: Magic Line price level
            notes: User notes about why this level matters
            line_color: Color for chart display (default 'purple')
            line_width: Line width for chart (default 2)
            line_style: 'Solid', 'Dashed', 'Dotted' (default 'Solid')
            active: Whether this Magic Line is active (default True)
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO magic_lines 
                        (symbol, magic_line_price, notes, line_color, line_width, line_style, active, updated_at)
                    VALUES 
                        (:symbol, :price, :notes, :color, :width, :style, :active, CURRENT_TIMESTAMP)
                    ON CONFLICT (symbol)
                    DO UPDATE SET
                        magic_line_price = EXCLUDED.magic_line_price,
                        notes = EXCLUDED.notes,
                        line_color = EXCLUDED.line_color,
                        line_width = EXCLUDED.line_width,
                        line_style = EXCLUDED.line_style,
                        active = EXCLUDED.active,
                        updated_at = CURRENT_TIMESTAMP
                """)
                
                conn.execute(query, {
                    'symbol': symbol,
                    'price': price,
                    'notes': notes,
                    'color': line_color,
                    'width': line_width,
                    'style': line_style,
                    'active': active
                })
                
                conn.commit()
                
                print(f"✓ Set Magic Line for {symbol}: {price:.2f}")
                if notes:
                    print(f"  Note: {notes}")
        
        except Exception as e:
            print(f"✗ Error setting Magic Line for {symbol}: {e}")
    
    def bulk_import(self, bulk_input: str):
        """
        Parse and import Magic Lines from bulk format
        
        Format: "SYMBOL:VALUE, SYMBOL:VALUE, ..."
        Example: "BTC/USDT:90000, ETH/USDT:3000, SOL/USDT:200"
        
        Matches Pine Script bulk import logic
        
        Args:
            bulk_input: Formatted string with symbol:price pairs
        """
        if not bulk_input or bulk_input.strip() == "":
            print("⚠️  Bulk input is empty")
            return
        
        try:
            # Split by comma
            pairs = bulk_input.split(',')
            
            count = 0
            for pair in pairs:
                pair = pair.strip()
                
                # Split by colon
                if ':' not in pair:
                    print(f"  ⚠️  Skipping invalid format: {pair}")
                    continue
                
                parts = pair.split(':')
                if len(parts) != 2:
                    print(f"  ⚠️  Skipping invalid format: {pair}")
                    continue
                
                symbol = parts[0].strip().upper()
                
                # Add /USDT if not present (for convenience)
                if '/' not in symbol:
                    symbol = symbol + '/USDT'
                
                try:
                    price = float(parts[1].strip())
                    
                    # Set Magic Line
                    self.set_magic_line(symbol, price, notes=f"Bulk import on {self._get_current_time()}")
                    count += 1
                
                except ValueError:
                    print(f"  ✗ Invalid price for {symbol}: {parts[1]}")
            
            print(f"\n✅ Bulk import complete: {count} Magic Lines imported")
        
        except Exception as e:
            print(f"✗ Error in bulk import: {e}")
    
    def get_magic_line(self, symbol: str) -> Optional[float]:
        """
        Get Magic Line price for symbol
        
        Returns:
            Magic Line price (float) or None if not set
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT magic_line_price
                    FROM magic_lines
                    WHERE symbol = :symbol
                      AND active = true
                """)
                
                result = conn.execute(query, {'symbol': symbol}).fetchone()
                
                if result:
                    return float(result[0])
                else:
                    return None
        
        except Exception as e:
            print(f"Error getting Magic Line for {symbol}: {e}")
            return None
    
    def get_all_magic_lines(self, active_only: bool = True) -> List[Dict]:
        """
        Get all Magic Lines
        
        Args:
            active_only: Only return active Magic Lines (default True)
        
        Returns:
            List of dicts with symbol, price, notes, etc.
        """
        try:
            with self.engine.connect() as conn:
                if active_only:
                    query = text("""
                        SELECT symbol, magic_line_price, notes, line_color, line_width, line_style, active
                        FROM magic_lines
                        WHERE active = true
                        ORDER BY symbol
                    """)
                else:
                    query = text("""
                        SELECT symbol, magic_line_price, notes, line_color, line_width, line_style, active
                        FROM magic_lines
                        ORDER BY symbol
                    """)
                
                result = conn.execute(query)
                
                magic_lines = []
                for row in result:
                    magic_lines.append({
                        'symbol': row[0],
                        'price': float(row[1]),
                        'notes': row[2] or '',
                        'color': row[3],
                        'width': row[4],
                        'style': row[5],
                        'active': row[6]
                    })
                
                return magic_lines
        
        except Exception as e:
            print(f"Error getting Magic Lines: {e}")
            return []
    
    def check_price_vs_magic_line(self, symbol: str, current_price: float) -> Dict:
        """
        Compare current price to Magic Line
        
        Returns:
            {
                'magic_line': float or None,
                'status': 'ABOVE' / 'BELOW' / 'AT' / 'NOT_SET',
                'distance_pct': float (percentage distance)
            }
        """
        magic_line = self.get_magic_line(symbol)
        
        if magic_line is None:
            return {
                'magic_line': None,
                'status': 'NOT_SET',
                'distance_pct': 0.0
            }
        
        distance_pct = ((current_price - magic_line) / magic_line) * 100
        
        # Determine status (within 0.5% = AT)
        if abs(distance_pct) <= 0.5:
            status = 'AT'
        elif current_price > magic_line:
            status = 'ABOVE'
        else:
            status = 'BELOW'
        
        return {
            'magic_line': magic_line,
            'status': status,
            'distance_pct': distance_pct
        }
    
    def delete_magic_line(self, symbol: str):
        """
        Delete Magic Line for symbol
        """
        try:
            with self.engine.connect() as conn:
                query = text("DELETE FROM magic_lines WHERE symbol = :symbol")
                conn.execute(query, {'symbol': symbol})
                conn.commit()
                print(f"✓ Deleted Magic Line for {symbol}")
        
        except Exception as e:
            print(f"✗ Error deleting Magic Line: {e}")
    
    def deactivate_magic_line(self, symbol: str):
        """
        Deactivate Magic Line (soft delete)
        """
        try:
            with self.engine.connect() as conn:
                query = text("UPDATE magic_lines SET active = false WHERE symbol = :symbol")
                conn.execute(query, {'symbol': symbol})
                conn.commit()
                print(f"✓ Deactivated Magic Line for {symbol}")
        
        except Exception as e:
            print(f"✗ Error deactivating Magic Line: {e}")
    
    def _get_current_time(self):
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("MAGIC LINE MANAGER TEST")
    print("=" * 80)
    
    manager = MagicLineManager()
    
    # Test 1: Set individual Magic Lines
    print("\n" + "─" * 80)
    print("TEST 1: Setting Individual Magic Lines")
    print("─" * 80)
    
    manager.set_magic_line('BTC/USDT', 90000.0, notes="Psychological resistance level")
    manager.set_magic_line('ETH/USDT', 3000.0, notes="Round number target")
    
    # Test 2: Bulk import
    print("\n" + "─" * 80)
    print("TEST 2: Bulk Import")
    print("─" * 80)
    
    bulk_string = "BTC/USDT:95000, ETH/USDT:3200, SOL/USDT:200, ADA/USDT:1.5"
    print(f"Bulk input: {bulk_string}\n")
    manager.bulk_import(bulk_string)
    
    # Test 3: Get all Magic Lines
    print("\n" + "─" * 80)
    print("TEST 3: Retrieve All Magic Lines")
    print("─" * 80)
    
    all_lines = manager.get_all_magic_lines()
    for ml in all_lines:
        print(f"  {ml['symbol']}: ${ml['price']:.2f} - {ml['notes']}")
    
    # Test 4: Check price vs Magic Line
    print("\n" + "─" * 80)
    print("TEST 4: Price Comparison")
    print("─" * 80)
    
    test_prices = {
        'BTC/USDT': 87500.0,
        'ETH/USDT': 2950.0,
        'SOL/USDT': 205.0
    }
    
    for symbol, price in test_prices.items():
        result = manager.check_price_vs_magic_line(symbol, price)
        if result['status'] != 'NOT_SET':
            print(f"  {symbol}: ${price:.2f}")
            print(f"    Magic Line: ${result['magic_line']:.2f}")
            print(f"    Status: {result['status']}")
            print(f"    Distance: {result['distance_pct']:+.2f}%")
    
    print("\n" + "=" * 80)
    print("✅ MAGIC LINE MANAGER TEST COMPLETE!")
    print("=" * 80)
    print("\n💡 Verify in Navicat:")
    print("   SELECT * FROM magic_lines ORDER BY symbol;")