import os
import requests
from datetime import datetime
from typing import Dict, List
from functools import lru_cache
import time
import random
from dotenv import load_dotenv

load_dotenv()

# -------------------- Rate Limiting Decorator ------------------------

def rate_limit(min_interval=2):
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

# -------------------- Main Class ------------------------

class IndianStockData:
    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        self.base_url = "https://financialmodelingprep.com/api/v3"

    # -------------------- Get Stock Info ------------------------

    @rate_limit(1)
    @lru_cache(maxsize=100)
    def get_stock_info(self, symbol: str) -> Dict:
        try:
            url = f"{self.base_url}/quote/{symbol.upper()}?apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()

            if not data or not isinstance(data, list):
                return {"error": "Invalid response from API"}

            stock = data[0]
            return {
                "symbol": stock.get("symbol"),
                "company_name": stock.get("name", "N/A"),
                "current_price": round(stock.get("price", 0), 2),
                "previous_close": round(stock.get("previousClose", 0), 2),
                "change": round(stock.get("change", 0), 2),
                "change_percent": round(stock.get("changesPercentage", 0), 2),
                "volume": stock.get("volume"),
                "market_cap": stock.get("marketCap", "N/A"),
                "pe_ratio": stock.get("pe", "N/A"),
                "dividend_yield": stock.get("lastDiv", "N/A"),
                "52_week_high": stock.get("yearHigh", "N/A"),
                "52_week_low": stock.get("yearLow", "N/A"),
                "sector": "N/A",  # Not available from this endpoint
                "industry": "N/A"
            }

        except Exception as e:
            return {"error": f"Failed to fetch data for {symbol}: {str(e)}"}

    # -------------------- Get Historical Data ------------------------

    @rate_limit(1)
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Dict:
        try:
            url = f"{self.base_url}/historical-price-full/{symbol.upper()}?apikey={self.api_key}&serietype=line"
            response = requests.get(url)
            data = response.json()

            if not data or "historical" not in data:
                return {"error": "Historical data not available."}

            historical = data["historical"][:30] if period == "1mo" else data["historical"]

            hist_data = [
                {
                    "date": entry["date"],
                    "close": round(entry["close"], 2)
                }
                for entry in historical
            ]

            return {
                "symbol": symbol.upper(),
                "period": period,
                "data": hist_data
            }

        except Exception as e:
            return {"error": f"Error fetching historical data: {str(e)}"}

    # -------------------- Get Top Gainers & Losers ------------------------

    @rate_limit(2)
    def get_top_gainers_losers(self) -> Dict:
        try:
            gainers = requests.get(f"{self.base_url}/stock_market/gainers?apikey={self.api_key}").json()
            losers = requests.get(f"{self.base_url}/stock_market/losers?apikey={self.api_key}").json()
            return {
                "top_gainers": gainers[:5],
                "top_losers": losers[:5],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"Failed to fetch gainers/losers: {str(e)}"}

    # -------------------- Search Stock Symbol ------------------------

    def search_stocks(self, query: str) -> List[Dict]:
        try:
            url = f"{self.base_url}/search?query={query}&limit=10&exchange=NASDAQ&apikey={self.api_key}"
            response = requests.get(url)
            return response.json()
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]
