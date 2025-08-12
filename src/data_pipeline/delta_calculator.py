"""
Delta Calculator - Calculates day-over-day changes in OI data
Identifies patterns and unusual activity for LLM analysis
"""

from datetime import datetime

class DeltaCalculator:
    def __init__(self):
        pass
    
    def calculate_deltas(self, current_data, previous_data, ticker):
        """Calculate comprehensive deltas between current and previous day OI data"""
        if not previous_data:
            return self._create_baseline_delta(current_data, ticker)
        
        # Get the latest date data from current
        data_by_date = current_data.get("data_by_date", {})
        if not data_by_date:
            return {"ticker": ticker, "error": "No current data available"}
        current_date_key = max(data_by_date.keys())
        current_oi = data_by_date[current_date_key]
        
        # Get the latest date data from previous
        previous_dates = previous_data.get("data_by_date", {})
        if not previous_dates:
            return {"ticker": ticker, "error": "No previous data available"}
        previous_date_key = max(previous_dates.keys())
        previous_oi = previous_dates[previous_date_key]
        
        delta_data = {
            "ticker": ticker,
            "current_date": current_date_key,
            "previous_date": previous_date_key,
            "timestamp": datetime.now().isoformat(),
            
            # Basic ratio changes
            "put_call_ratio_delta": current_oi.get("put_call_ratio", 0) - previous_oi.get("put_call_ratio", 0),
            "max_pain_shift": current_oi.get("max_pain", 0) - previous_oi.get("max_pain", 0),
            
            # Total OI changes
            "total_oi_change": current_oi.get("total_oi", 0) - previous_oi.get("total_oi", 0),
            "call_oi_change": current_oi.get("call_oi", 0) - previous_oi.get("call_oi", 0),
            "put_oi_change": current_oi.get("put_oi", 0) - previous_oi.get("put_oi", 0),
            
            # Percentage changes
            "total_oi_pct_change": self._calculate_percentage_change(
                previous_oi.get("total_oi", 0), 
                current_oi.get("total_oi", 0)
            ),
            "call_oi_pct_change": self._calculate_percentage_change(
                previous_oi.get("call_oi", 0), 
                current_oi.get("call_oi", 0)
            ),
            "put_oi_pct_change": self._calculate_percentage_change(
                previous_oi.get("put_oi", 0), 
                current_oi.get("put_oi", 0)
            ),
            
            # Strike level analysis
            "strike_level_changes": self._analyze_strike_changes(
                current_oi.get("strikes", {}), 
                previous_oi.get("strikes", {})
            ),
            
            # New strikes detection
            "new_call_strikes": self._find_new_strikes(
                current_oi.get("strikes", {}).get("calls", {}),
                previous_oi.get("strikes", {}).get("calls", {})
            ),
            "new_put_strikes": self._find_new_strikes(
                current_oi.get("strikes", {}).get("puts", {}),
                previous_oi.get("strikes", {}).get("puts", {})
            ),
            
            # Large block detection
            "large_oi_increases": self._detect_large_blocks(
                current_oi.get("strikes", {}), 
                previous_oi.get("strikes", {}),
                threshold=5000
            ),
            
            # Unusual activity flags
            "unusual_activity": self._detect_unusual_activity(current_oi, previous_oi),
            
            # Weighted average shifts
            "call_weighted_avg_shift": self._calculate_weighted_avg_shift(
                current_oi.get("weighted_averages", {}),
                previous_oi.get("weighted_averages", {}),
                "call_weighted_avg"
            ),
            "put_weighted_avg_shift": self._calculate_weighted_avg_shift(
                current_oi.get("weighted_averages", {}),
                previous_oi.get("weighted_averages", {}),
                "put_weighted_avg"
            ),
        }
        
        return delta_data
    
    def _create_baseline_delta(self, current_data, ticker):
        """Create baseline delta when no previous data exists"""
        data_by_date = current_data.get("data_by_date", {})
        if not data_by_date:
            return {"ticker": ticker, "error": "No data available"}
        current_date_key = max(data_by_date.keys())
        current_oi = data_by_date[current_date_key]
        
        return {
            "ticker": ticker,
            "current_date": current_date_key,
            "previous_date": None,
            "timestamp": datetime.now().isoformat(),
            "is_baseline": True,
            "put_call_ratio": current_oi.get("put_call_ratio", 0),
            "max_pain": current_oi.get("max_pain", 0),
            "total_oi": current_oi.get("total_oi", 0),
            "message": "No previous data available - baseline established"
        }
    
    def _calculate_percentage_change(self, old_value, new_value):
        """Calculate percentage change with division by zero protection"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return ((new_value - old_value) / old_value) * 100
    
    def _analyze_strike_changes(self, current_strikes, previous_strikes):
        """Analyze changes at individual strike levels"""
        changes = {"calls": {}, "puts": {}}
        
        for option_type in ["calls", "puts"]:
            current_type_strikes = current_strikes.get(option_type, {})
            previous_type_strikes = previous_strikes.get(option_type, {})
            
            # Check all strikes that exist in either current or previous
            all_strikes = set(current_type_strikes.keys()) | set(previous_type_strikes.keys())
            
            for strike in all_strikes:
                current_oi = current_type_strikes.get(strike, 0)
                previous_oi = previous_type_strikes.get(strike, 0)
                
                if current_oi != previous_oi:
                    changes[option_type][strike] = {
                        "current": current_oi,
                        "previous": previous_oi,
                        "change": current_oi - previous_oi,
                        "pct_change": self._calculate_percentage_change(previous_oi, current_oi)
                    }
        
        return changes
    
    def _find_new_strikes(self, current_strikes, previous_strikes):
        """Find strikes that didn't exist in previous data"""
        current_set = set(current_strikes.keys())
        previous_set = set(previous_strikes.keys())
        new_strikes = current_set - previous_set
        
        return [
            {
                "strike": strike,
                "oi": current_strikes[strike]
            }
            for strike in new_strikes
        ]
    
    def _detect_large_blocks(self, current_strikes, previous_strikes, threshold=5000):
        """Detect unusually large OI increases that might indicate institutional activity"""
        large_blocks = []
        
        for option_type in ["calls", "puts"]:
            current_type = current_strikes.get(option_type, {})
            previous_type = previous_strikes.get(option_type, {})
            
            for strike in current_type:
                current_oi = current_type.get(strike, 0)
                previous_oi = previous_type.get(strike, 0)
                change = current_oi - previous_oi
                
                if change >= threshold:
                    large_blocks.append({
                        "type": option_type[:-1],  # "calls" -> "call"
                        "strike": strike,
                        "oi_increase": change,
                        "current_oi": current_oi,
                        "previous_oi": previous_oi
                    })
        
        return large_blocks
    
    def _detect_unusual_activity(self, current_oi, previous_oi):
        """Flag unusual activity patterns"""
        flags = []
        
        # Large put/call ratio shifts
        pcr_change = abs(current_oi.get("put_call_ratio", 0) - previous_oi.get("put_call_ratio", 0))
        if pcr_change > 0.3:
            flags.append(f"Large P/C ratio shift: {pcr_change:.2f}")
        
        # Significant max pain movement
        max_pain_shift = abs(current_oi.get("max_pain", 0) - previous_oi.get("max_pain", 0))
        if max_pain_shift > 10:  # $10 move
            flags.append(f"Max pain moved ${max_pain_shift:.2f}")
        
        # Large total OI changes
        total_oi_change_pct = self._calculate_percentage_change(
            previous_oi.get("total_oi", 0),
            current_oi.get("total_oi", 0)
        )
        if abs(total_oi_change_pct) > 20:
            flags.append(f"Total OI changed {total_oi_change_pct:.1f}%")
        
        return flags
    
    def _calculate_weighted_avg_shift(self, current_weighted, previous_weighted, field):
        """Calculate shift in weighted averages"""
        current_value = current_weighted.get(field, 0)
        previous_value = previous_weighted.get(field, 0)
        return current_value - previous_value