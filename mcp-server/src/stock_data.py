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
                time.sleep(min_interval - elapsed + random.uniform(0.1, 0.3))
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

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
        """Get detailed stock information with fallback logic"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)

            # Try using fast_info first (preferred)
            fast_info = stock.fast_info
            if fast_info and 'last_price' in fast_info:
                current_price = fast_info['last_price']
                previous_close = fast_info.get('previous_close', current_price)
                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close else 0

                return {
                    "symbol": symbol.upper(),
                    "company_name": stock.info.get('longName', symbol.upper()),
                    "current_price": round(current_price, 2),
                    "previous_close": round(previous_close, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": fast_info.get('last_volume', 'N/A'),
                    "market_cap": fast_info.get('market_cap', 'N/A'),
                    "pe_ratio": stock.info.get('trailingPE', 'N/A'),
                    "dividend_yield": stock.info.get('dividendYield', 'N/A'),
                    "52_week_high": stock.info.get('fiftyTwoWeekHigh', 'N/A'),
                    "52_week_low": stock.info.get('fiftyTwoWeekLow', 'N/A'),
                    "sector": stock.info.get('sector', 'N/A'),
                    "industry": stock.info.get('industry', 'N/A')
                }

            # Fallback to history if fast_info fails
            return self._fallback_stock_info(symbol)

        except Exception:
            return {"error": f"Unable to fetch data for {symbol.upper()}. Please try again later."}

    def _fallback_stock_info(self, symbol: str) -> Dict:
        """Fallback using intraday historical data"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)
            hist = stock.history(period="1d", interval="1m")

            if hist.empty:
                return {"error": f"No fallback price data available for {symbol.upper()}"}

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
                "volume": int(hist['Volume'].iloc[-1]),
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "dividend_yield": "N/A",
                "52_week_high": "N/A",
                "52_week_low": "N/A",
                "sector": "N/A",
                "industry": "N/A"
            }

        except Exception:
            return {"error": f"Could not fetch fallback data for {symbol.upper()}."}

    # ---------- Historical Chart Data ----------

    @rate_limit(1)
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Dict:
        """Get historical stock data"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)
            hist = stock.history(period=period)

            if hist.empty:
                return {"error": f"No historical data found for {symbol.upper()}"}

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
        except Exception:
            return {"error": f"Could not retrieve historical data for {symbol.upper()}"}

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
