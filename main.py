import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from schwab.auth import client_from_token_file
from schwab.history import HistoryClient
import config
from strategy import ORBStrategy

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_market_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch market data from Schwab API."""
    try:
        # Create Schwab client
        client = client_from_token_file(
            token_path=config.TOKEN_PATH,
            api_key=config.API_KEY,
            app_secret=config.APP_SECRET
        )
        
        # Create history client
        history_client = HistoryClient(client)
        
        # Convert dates to timestamps
        start_ts = int(pd.Timestamp(start_date).timestamp())
        end_ts = int(pd.Timestamp(end_date).timestamp())
        
        # Get historical data
        data = history_client.get_history(
            symbol=symbol,
            interval='1',  # 1-minute candles
            start=start_ts,
            end=end_ts
        )
        
        if not data:
            logger.warning(f"No data received for {symbol}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
        df.set_index('datetime', inplace=True)
        df = df[['open', 'high', 'low', 'close']]
        df.sort_index(ascending=True, inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def run_strategy(symbol: str, start_date: str, end_date: str) -> dict:
    """Run the ORB strategy for a single symbol."""
    # Get market data
    df = get_market_data(symbol, start_date, end_date)
    if df is None:
        return None
    
    # Initialize strategy
    strategy = ORBStrategy(config)
    
    # Group data by date
    df['date'] = df.index.date
    
    # Process each trading day
    for date, day_data in df.groupby('date'):
        # Skip if not enough data for range calculation
        if len(day_data) < config.RANGE_CANDLES:
            continue
        
        # Calculate opening range
        range_high, range_low = strategy.calculate_range(day_data, config.RANGE_CANDLES)
        
        # Process each candle after the range period
        for idx, candle in day_data.iloc[config.RANGE_CANDLES:].iterrows():
            strategy.process_candle(symbol, candle, range_high, range_low)
    
    # Calculate and return statistics
    return strategy.calculate_statistics()

def main():
    """Main function to run the strategy."""
    # Set date range
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Create results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    
    # Run strategy for each symbol
    results = {}
    for symbol in config.SYMBOLS:
        logger.info(f"Running strategy for {symbol}")
        stats = run_strategy(symbol, start_date, end_date)
        if stats:
            results[symbol] = stats
    
    # Save results to CSV
    if results:
        df_results = pd.DataFrame(results).T
        df_results.to_csv(f'results/strategy_results_{end_date}.csv')
        logger.info(f"Results saved to results/strategy_results_{end_date}.csv")
        
        # Print summary
        print("\nStrategy Results Summary:")
        print("=" * 50)
        print(f"Total Symbols: {len(results)}")
        print(f"Average Win Rate: {df_results['win_rate'].mean():.2f}%")
        print(f"Average PnL: {df_results['avg_pnl'].mean():.2f}%")
        print(f"Average Profit Factor: {df_results['profit_factor'].mean():.2f}")
        print(f"Average Max Drawdown: {df_results['max_drawdown'].mean():.2f}%")

if __name__ == "__main__":
    main()
