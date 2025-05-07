import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('SCHWAB_API_KEY')
APP_SECRET = os.getenv('SCHWAB_APP_SECRET')
TOKEN_PATH = os.getenv('SCHWAB_TOKEN_PATH', 'token.json')

# Trading Configuration
INITIAL_CAPITAL = 100000
POSITION_SIZE = 0.5  # 50% of capital per trade
STOP_LOSS_DISTANCE = 0.25  # Distance from entry price for stop loss
TARGET_MULTIPLIER = 2.0  # Multiplier for target calculation
RANGE_CANDLES = 10  # Number of candles for initial range
BREAKOUT_MIN = 0.20  # Minimum distance required for breakout signal

# Market Hours (Eastern Time)
MARKET_OPEN = "09:30"
MARKET_CLOSE = "16:00"
FORCED_CLOSE = "15:55"

# Trading Symbols
SYMBOLS = [
    "AAPL", "TSLA", "META", "NFLX", "AMZN", "GOOGL", 
    "MSFT", "JPM", "NVDA", "PLTR", "ROKU", "V", 
    "TGT", "SPY", "QQQ", "DIA"
] 