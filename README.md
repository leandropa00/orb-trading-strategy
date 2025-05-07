# ThinkOrSwim ORB Strategy

This project implements an Opening Range Breakout (ORB) trading strategy using the Schwab API. The strategy is based on the original ThinkOrSwim implementation but adapted to work with Python and the Schwab API.

## Features

- Opening Range Breakout strategy implementation
- Support for multiple symbols
- Real-time market data integration with Schwab API
- Performance tracking and statistics
- Configurable parameters
- Detailed trade logging

## Requirements

- Python 3.8+
- Schwab API credentials
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/leandropa00/orb-trading-strategy.git
cd orb-trading-strategy
```

2. Create and activate a virtual environment:

For Linux/Mac:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

For Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Schwab API credentials:
```
SCHWAB_API_KEY=your_api_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_TOKEN_PATH=path_to_token_file
```

5. Deactivate virtual environment when done:
```bash
deactivate
```

## Configuration

The strategy parameters can be configured in `config.py`:

- `INITIAL_CAPITAL`: Starting capital for the strategy
- `POSITION_SIZE`: Percentage of capital to use per trade
- `STOP_LOSS_DISTANCE`: Distance from entry price for stop loss
- `TARGET_MULTIPLIER`: Multiplier for target calculation
- `RANGE_CANDLES`: Number of candles for initial range
- `BREAKOUT_MIN`: Minimum distance required for breakout signal
- `SYMBOLS`: List of symbols to trade

## Usage

1. Activate the virtual environment (if not already activated):

For Linux/Mac:
```bash
source venv/bin/activate
```

For Windows:
```bash
.\venv\Scripts\activate
```

2. Run the strategy:
```bash
python main.py
```

The script will:
1. Fetch market data for each symbol
2. Calculate opening ranges
3. Execute trades based on breakout signals
4. Track performance and generate statistics
5. Save results to CSV in the `results` directory

## Strategy Logic

1. Calculate the opening range using the first N candles of the trading day
2. Wait for a breakout signal:
   - Long: Price breaks above range high + minimum breakout distance
   - Short: Price breaks below range low - minimum breakout distance
3. Enter position with stop loss and target:
   - Stop loss: Entry price ± stop loss distance
   - Target: Entry price ± (range size * target multiplier)
4. Exit position when either stop loss or target is hit

## Results

The strategy generates the following statistics for each symbol:
- Total number of trades
- Win rate
- Average PnL
- Maximum drawdown
- Profit factor
- Final capital

Results are saved to CSV files in the `results` directory with timestamps.

## Virtual Environment Management

### Creating a new virtual environment
```bash
python3 -m venv venv  # Linux/Mac
python -m venv venv   # Windows
```

### Activating the virtual environment
```bash
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

### Deactivating the virtual environment
```bash
deactivate
```

### Updating packages
```bash
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### Removing the virtual environment
```bash
rm -rf venv  # Linux/Mac
rmdir /s /q venv  # Windows
```