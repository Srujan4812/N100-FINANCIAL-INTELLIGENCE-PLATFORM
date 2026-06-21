from typing import Optional

def compute_fcf(cfo: float, cfi: float) -> float:
    """Free Cash Flow = CFO + CFI"""
    cfo_val = cfo if cfo is not None else 0.0
    cfi_val = cfi if cfi is not None else 0.0
    return cfo_val + cfi_val

def compute_fcf_conversion(fcf: float, ebitda: float) -> Optional[float]:
    """FCF Conversion Rate = FCF / EBITDA (EBITDA is operating_profit)"""
    if ebitda == 0 or ebitda is None:
        return None
    fcf_val = fcf if fcf is not None else 0.0
    return (fcf_val / ebitda) * 100

def compute_capex_intensity(cfi: float, sales: float) -> Optional[float]:
    """CapEx Intensity = abs(CFI) / Sales * 100 (CFI is used as proxy for CapEx)"""
    if sales == 0 or sales is None:
        return None
    cfi_val = cfi if cfi is not None else 0.0
    return (abs(cfi_val) / sales) * 100

def get_capex_category(intensity: Optional[float]) -> str:
    """Categorise CapEx intensity."""
    if intensity is None:
        return "Unknown"
    if intensity < 3.0:
        return "asset-light"
    elif intensity > 8.0:
        return "capital intensive"
    else:
        return "medium"

def compute_cfo_quality(cfo: float, pat: float) -> Optional[float]:
    """CFO Quality Score = CFO / PAT (operating_activity / net_profit)"""
    if pat == 0 or pat is None:
        return None
    cfo_val = cfo if cfo is not None else 0.0
    return cfo_val / pat

def get_cfo_quality_category(avg_5yr_quality: Optional[float]) -> str:
    """Categorise 5-year average CFO quality score."""
    if avg_5yr_quality is None:
        return "Unknown"
    if avg_5yr_quality > 1.0:
        return "High Quality Earnings"
    elif avg_5yr_quality < 0.5:
        return "Accrual Risk"
    else:
        return "Normal"

def classify_capital_allocation(cfo: float, cfi: float, cff: float) -> str:
    """
    Classifies capital allocation patterns based on sign of CFO, CFI, CFF:
    - CFO>0, CFI<0, CFF<0: Reinvestor (if abs(CFI) >= abs(CFF)) or Shareholder Returns (if abs(CFF) > abs(CFI))
    - CFO<0, CFF>0: Distress
    - Maps all 8 standard sign permutations to descriptive classes.
    """
    cfo_val = cfo if cfo is not None else 0.0
    cfi_val = cfi if cfi is not None else 0.0
    cff_val = cff if cff is not None else 0.0

    cfo_sign = '+' if cfo_val >= 0 else '-'
    cfi_sign = '+' if cfi_val >= 0 else '-'
    cff_sign = '+' if cff_val >= 0 else '-'
    
    pattern = (cfo_sign, cfi_sign, cff_sign)
    
    if pattern == ('+', '-', '-'):
        # Sub-classify by spending weight
        if abs(cfi_val) >= abs(cff_val):
            return "Reinvestor"
        else:
            return "Shareholder Returns"
            
    elif cfo_sign == '-' and cff_sign == '+':
        return "Distress"  # Raising finance to cover operating cash burn
        
    elif pattern == ('+', '-', '+'):
        return "Growth Expansion"
        
    elif pattern == ('+', '+', '-'):
        return "Divest & Repay"
        
    elif pattern == ('+', '+', '+'):
        return "Cash Accumulation"
        
    elif pattern == ('-', '-', '-'):
        return "Distress (Cash Burn)"
        
    elif pattern == ('-', '+', '-'):
        return "Restructuring"
        
    else:
        # Default fallback
        if cfo_sign == '-':
            return "Distress"
        return "Other"
