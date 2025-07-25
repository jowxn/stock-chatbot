import os
from dotenv import load_dotenv

load_dotenv()

# MCP Server Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

# Streamlit Configuration
STREAMLIT_CONFIG = {
    "page_title": "Indian Stock Market Chatbot",
    "page_icon": "📈",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Chat Configuration
CHAT_CONFIG = {
    "max_messages": 50,
    "welcome_message": "Hello! I'm your Indian Stock Market assistant. Ask me about stock prices, market trends, or any stock-related queries!"
}