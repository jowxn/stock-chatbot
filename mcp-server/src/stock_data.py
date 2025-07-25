import yfinance as yf
import pandas as pd
import requests
from typing import Dict, List
import json
from datetime import datetime
import time
import random
from functools import lru_cache

# -------------- [ Rate Limiting + Session Setup ] --------------------

def rate_limit(min_interval=2):
    """Decorator to add rate limiting"""
    def decorator(func):
        last_called = [0.0]
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed + random.uniform(0.1, 0.4))
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

def configure_yfinance():
    """Custom session with headers"""
    session = yf.utils.requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive'
    })
    return session

# -------------- [ Main Stock Data Class ] --------------------

class IndianStockData:
    def __init__(self):
        self.nse_symbols = {}
        self.load_nse_symbols()
    
    def load_nse_symbols(self):
        """Load NSE stock symbols mapping"""
        self.nse_symbols = {
            "RELIANCE": "RELIANCE.NS",
            "TCS": "TCS.NS",
            "INFY": "INFY.NS",
            "HDFCBANK": "HDFCBANK.NS",
            "ICICIBANK": "ICICIBANK.NS",
            "HINDUNILVR": "HINDUNILVR.NS",
            "SBIN": "SBIN.NS",
            "BHARTIARTL": "BHARTIARTL.NS",
            "ITC": "ITC.NS",
            "KOTAKBANK": "KOTAKBANK.NS",
            "LT": "LT.NS",
            "ASIANPAINT": "ASIANPAINT.NS",
            "MARUTI": "MARUTI.NS",
            "BAJFINANCE": "BAJFINANCE.NS",
            "HCLTECH": "HCLTECH.NS"
        }

    # ---------- Enhanced Stock Info Function ----------
    
    @rate_limit(2)
    @lru_cache(maxsize=128)
    def get_stock_info(self, symbol: str) -> Dict:
        """Get detailed stock information with caching and fallback"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            session = configure_yfinance()
            stock = yf.Ticker(yf_symbol, session=session)
            info = stock.info

            if not info or 'regularMarketPrice' not in info:
                return self._fallback_stock_info(symbol)

            current_price = info.get('regularMarketPrice')
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close else 0

            return {
                "symbol": symbol.upper(),
                "company_name": info.get('longName', 'N/A'),
                "current_price": round(current_price, 2),
                "previous_close": round(previous_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume', 'N/A'),
                "market_cap": info.get('marketCap', 'N/A'),
                "pe_ratio": info.get('trailingPE', 'N/A'),
                "dividend_yield": info.get('dividendYield', 'N/A'),
                "52_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
                "52_week_low": info.get('fiftyTwoWeekLow', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A')
            }

        except Exception as e:
            return {"error": f"Error fetching data for {symbol}: {str(e)}"}

    def _fallback_stock_info(self, symbol: str) -> Dict:
        """Fallback using historical data if .info fails"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)
            hist = stock.history(period="5d")

            if hist.empty:
                return {"error": "No fallback data available."}

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_price
            change_percent = (change / prev_price * 100) if prev_price else 0

            return {
                "symbol": symbol.upper(),
                "company_name": symbol.upper(),
                "current_price": round(current_price, 2),
                "previous_close": round(prev_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": hist['Volume'].iloc[-1],
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "dividend_yield": "N/A",
                "52_week_high": "N/A",
                "52_week_low": "N/A",
                "sector": "N/A",
                "industry": "N/A"
            }

        except Exception as e:
            return {"error": f"Fallback failed: {str(e)}"}

    # ---------- Historical Chart Data ----------
    
    @rate_limit(1)
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Dict:
        """Get historical stock data"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)
            hist = stock.history(period=period)

            if hist.empty:
                return {"error": f"No historical data found for {symbol}"}

            hist_data = []
            for date, row in hist.iterrows():
                hist_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })

            return {
                "symbol": symbol.upper(),
                "period": period,
                "data": hist_data
            }
        except Exception as e:
            return {"error": f"Error fetching historical data for {symbol}: {str(e)}"}

    # ---------- Gainers and Losers ----------
    
    @rate_limit(2)
    def get_top_gainers_losers(self) -> Dict:
        """Get top gainers and losers from major Indian stocks"""
        stocks_data = []

        for symbol in list(self.nse_symbols.keys())[:10]:  # Top 10 stocks
            data = self.get_stock_info(symbol)
            if "error" not in data:
                stocks_data.append(data)

        gainers = sorted(
            [s for s in stocks_data if s.get('change_percent', 0) > 0],
            key=lambda x: x.get('change_percent', 0),
            reverse=True
        )[:5]

        losers = sorted(
            [s for s in stocks_data if s.get('change_percent', 0) < 0],
            key=lambda x: x.get('change_percent', 0)
        )[:5]

        return {
            "top_gainers": gainers,
            "top_losers": losers,
            "timestamp": datetime.now().isoformat()
        }

    # ---------- Search Stocks ----------
    
    def search_stocks(self, query: str) -> List[Dict]:
        """Search for stocks based on query"""
        results = []
        query_lower = query.lower()

        for symbol, yf_symbol in self.nse_symbols.items():
            if query_lower in symbol.lower():
                try:
                    stock = yf.Ticker(yf_symbol)
                    info = stock.info
                    results.append({
                        "symbol": symbol,
                        "company_name": info.get('longName', 'N/A'),
                        "sector": info.get('sector', 'N/A')
                    })
                except:
                    results.append({
                        "symbol": symbol,
                        "company_name": "N/A",
                        "sector": "N/A"
                    })

        return results[:10]
