from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
from stock_data import IndianStockData
from utils import format_currency, format_percentage
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Indian Stock Market MCP Server", version="1.0.0")
stock_data = IndianStockData()

# Request/Response Models
class StockRequest(BaseModel):
    symbol: str

class HistoricalRequest(BaseModel):
    symbol: str
    period: Optional[str] = "1mo"

class SearchRequest(BaseModel):
    query: str

class MCPRequest(BaseModel):
    method: str
    params: Dict

# MCP Endpoints
@app.get("/")
async def root():
    return {"message": "Indian Stock Market MCP Server", "status": "running"}

@app.post("/mcp")
async def mcp_handler(request: MCPRequest):
    """Main MCP handler for all stock-related queries"""
    try:
        method = request.method
        params = request.params
        
        if method == "get_stock_info":
            symbol = params.get("symbol")
            if not symbol:
                raise HTTPException(status_code=400, detail="Symbol is required")
            result = stock_data.get_stock_info(symbol)
            
        elif method == "get_historical_data":
            symbol = params.get("symbol")
            period = params.get("period", "1mo")
            if not symbol:
                raise HTTPException(status_code=400, detail="Symbol is required")
            result = stock_data.get_historical_data(symbol, period)
            
        elif method == "get_top_gainers_losers":
            result = stock_data.get_top_gainers_losers()
            
        elif method == "search_stocks":
            query = params.get("query")
            if not query:
                raise HTTPException(status_code=400, detail="Query is required")
            result = stock_data.search_stocks(query)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
        
        return {
            "success": True,
            "data": result,
            "method": method
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "method": request.method
        }

# Direct REST endpoints (for easier testing)
@app.get("/stock/{symbol}")
async def get_stock(symbol: str):
    """Get stock information"""
    result = stock_data.get_stock_info(symbol)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/historical/{symbol}")
async def get_historical(symbol: str, period: str = "1mo"):
    """Get historical stock data"""
    result = stock_data.get_historical_data(symbol, period)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/market/movers")
async def get_market_movers():
    """Get top gainers and losers"""
    return stock_data.get_top_gainers_losers()

@app.get("/search/{query}")
async def search_stocks(query: str):
    """Search for stocks"""
    return stock_data.search_stocks(query)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
