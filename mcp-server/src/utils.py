def format_currency(amount):
    """Format currency in Indian format"""
    if amount == 'N/A' or amount is None:
        return 'N/A'
    
    try:
        if amount >= 10000000:  # 1 crore
            return f"₹{amount/10000000:.2f} Cr"
        elif amount >= 100000:  # 1 lakh
            return f"₹{amount/100000:.2f} L"
        else:
            return f"₹{amount:,.2f}"
    except:
        return str(amount)

def format_percentage(percent):
    """Format percentage with appropriate sign and color indication"""
    if percent == 'N/A' or percent is None:
        return 'N/A'
    
    try:
        sign = "+" if percent > 0 else ""
        return f"{sign}{percent:.2f}%"
    except:
        return str(percent)

def get_market_status():
    """Get Indian market status"""
    from datetime import datetime, time
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).time()
    
    market_open = time(9, 15)  # 9:15 AM
    market_close = time(15, 30)  # 3:30 PM
    
    if market_open <= now <= market_close:
        return "OPEN"
    else:
        return "CLOSED"