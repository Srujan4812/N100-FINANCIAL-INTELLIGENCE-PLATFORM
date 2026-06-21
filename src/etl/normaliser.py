import re
from typing import Any

def normalize_year(year_val: Any) -> str:
    """
    Normalise year values into the standard YYYY-MM format.
    Handles variations like 'Mar-23', 'Mar 23', 'March-2023', integers like 2023, etc.
    Returns 'PARSE_ERROR' if parsing fails.
    """
    if year_val is None:
        return "PARSE_ERROR"
    
    # If integer, assume March close of that year
    if isinstance(year_val, int):
        return f"{year_val}-03"
    
    if isinstance(year_val, float):
        if year_val.is_integer():
            return f"{int(year_val)}-03"
        return "PARSE_ERROR"

    year_str = str(year_val).strip()
    if not year_str:
        return "PARSE_ERROR"

    # Already in YYYY-MM format
    if re.match(r'^\d{4}-\d{2}$', year_str):
        return year_str

    # Just a 4-digit number
    if re.match(r'^\d{4}$', year_str):
        return f"{year_str}-03"

    # FY23 or FY2023
    fy_match = re.match(r'^FY\s*(\d{2,4})$', year_str, re.IGNORECASE)
    if fy_match:
        yr = fy_match.group(1)
        if len(yr) == 2:
            return f"20{yr}-03"
        return f"{yr}-03"

    # Clean separators
    cleaned = re.sub(r'[\s/]+', '-', year_str)
    parts = cleaned.split('-')
    
    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
        'january': '01', 'february': '02', 'march': '03', 'april': '04', 'june': '06',
        'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11',
        'december': '12'
    }

    if len(parts) >= 2:
        month_num = None
        year_num = None
        
        for part in parts:
            p_lower = part.lower()
            if p_lower in month_map:
                month_num = month_map[p_lower]
            elif part.isdigit():
                year_num = part
        
        if not month_num:
            for part in parts:
                p_lower = part.lower()
                for m_key, m_val in month_map.items():
                    if m_key in p_lower:
                        month_num = m_val
                        break
                if month_num:
                    break

        if month_num and year_num:
            if len(year_num) == 2:
                year_num = f"20{year_num}"
            return f"{year_num}-{month_num}"

    # Try searching for substring matches if splitting didn't yield clean parts
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    found_month = None
    for m in months:
        if re.search(m, year_str, re.IGNORECASE):
            month_map_simple = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            found_month = month_map_simple[m]
            break
            
    digits = re.findall(r'\d+', year_str)
    if found_month and digits:
        for d in digits:
            if len(d) in [2, 4]:
                yr = d
                if len(yr) == 2:
                    yr = f"20{yr}"
                return f"{yr}-{found_month}"

    return "PARSE_ERROR"

def normalize_ticker(company_id: Any) -> str:
    """
    Normalise company tickers by stripping whitespace and uppercasing.
    Returns 'MISSING' if empty or None.
    """
    if company_id is None:
        return "MISSING"
    ticker = str(company_id).strip().upper()
    if not ticker:
        return "MISSING"
    return ticker
