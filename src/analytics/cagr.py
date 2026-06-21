from typing import Tuple, Optional
import numpy as np

def compute_cagr(start_val: float, end_val: float, num_years: int) -> Tuple[Optional[float], str]:
    """
    Calculate the Compound Annual Growth Rate (CAGR).
    CAGR = ((end_val / start_val) ** (1 / num_years) - 1) * 100
    Handles edge cases as defined in the CAGR Edge Case Decision Table:
    - start_val > 0, end_val > 0: Computed normally
    - start_val > 0, end_val < 0: None, flag 'DECLINE_TO_LOSS'
    - start_val < 0, end_val > 0: None, flag 'TURNAROUND'
    - start_val < 0, end_val < 0: None, flag 'BOTH_NEGATIVE'
    - start_val == 0: None, flag 'ZERO_BASE'
    - num_years < 3: None, flag 'INSUFFICIENT'
    """
    if num_years < 3:
        return None, "INSUFFICIENT"
        
    if start_val == 0:
        return None, "ZERO_BASE"
        
    if start_val > 0 and end_val > 0:
        try:
            val = ((end_val / start_val) ** (1 / num_years) - 1) * 100
            return round(val, 2), ""
        except Exception:
            return None, "ERROR"
            
    if start_val > 0 and end_val <= 0:
        return None, "DECLINE_TO_LOSS"
        
    if start_val < 0 and end_val > 0:
        return None, "TURNAROUND"
        
    if start_val < 0 and end_val < 0:
        return None, "BOTH_NEGATIVE"

    return None, "ERROR"

def get_cagr_display_string(cagr_val: Optional[float], flag: str) -> str:
    """Helper to return standard display string for CAGR values."""
    if cagr_val is not None:
        return f"{cagr_val:.1f}%"
    
    mapping = {
        "DECLINE_TO_LOSS": "N/A — turned loss",
        "TURNAROUND": "Turnaround ↑",
        "BOTH_NEGATIVE": "N/A — both loss",
        "ZERO_BASE": "N/A — base=0",
        "INSUFFICIENT": "N/A — < 3yr",
    }
    return mapping.get(flag, "N/A")
