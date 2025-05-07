import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import logging
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ORBStrategy:
    def __init__(self, config):
        self.config = config
        self.positions: Dict[str, Dict] = {}
        self.capital = config.INITIAL_CAPITAL
        self.trade_log = []

    def calculate_range(self, df: pd.DataFrame, n_candles: int) -> Tuple[float, float]:
        """Calculate the opening range high and low."""
        range_df = df.iloc[:n_candles]
        range_high = range_df['high'].max()
        range_low = range_df['low'].min()
        return range_high, range_low

    def calculate_targets(self, entry_price: float, range_size: float, 
                         is_long: bool) -> Tuple[float, float]:
        """Calculate stop loss and target prices."""
        if is_long:
            stop_loss = entry_price * (1 - self.config.STOP_LOSS_DISTANCE)
            target = entry_price + (range_size * self.config.TARGET_MULTIPLIER)
        else:
            stop_loss = entry_price * (1 + self.config.STOP_LOSS_DISTANCE)
            target = entry_price - (range_size * self.config.TARGET_MULTIPLIER)
        return stop_loss, target

    def check_breakout(self, current_price: float, range_high: float, 
                      range_low: float) -> Optional[str]:
        """Check for breakout signals."""
        if current_price > range_high + self.config.BREAKOUT_MIN:
            return 'LONG'
        elif current_price < range_low - self.config.BREAKOUT_MIN:
            return 'SHORT'
        return None

    def process_candle(self, symbol: str, candle: pd.Series, 
                      range_high: float, range_low: float) -> None:
        """Process a single candle and execute trading logic."""
        current_price = candle['close']
        current_time = candle.name

        # Check if we have an open position
        if symbol in self.positions:
            position = self.positions[symbol]
            
            # Check for exit conditions
            if position['type'] == 'LONG':
                if candle['low'] <= position['stop_loss']:
                    self.close_position(symbol, position['stop_loss'], current_time)
                elif candle['high'] >= position['target']:
                    self.close_position(symbol, position['target'], current_time)
            else:  # SHORT position
                if candle['high'] >= position['stop_loss']:
                    self.close_position(symbol, position['stop_loss'], current_time)
                elif candle['low'] <= position['target']:
                    self.close_position(symbol, position['target'], current_time)
        
        # Check for new entry signals
        elif current_time.time() < datetime.strptime(self.config.FORCED_CLOSE, "%H:%M").time():
            signal = self.check_breakout(current_price, range_high, range_low)
            if signal:
                range_size = range_high - range_low
                stop_loss, target = self.calculate_targets(
                    current_price, range_size, signal == 'LONG'
                )
                
                self.positions[symbol] = {
                    'type': signal,
                    'entry_price': current_price,
                    'entry_time': current_time,
                    'stop_loss': stop_loss,
                    'target': target,
                    'size': self.capital * self.config.POSITION_SIZE
                }
                logger.info(f"Opened {signal} position in {symbol} at {current_price}")

    def close_position(self, symbol: str, exit_price: float, exit_time: datetime) -> None:
        """Close an existing position and record the trade."""
        position = self.positions[symbol]
        entry_price = position['entry_price']
        
        if position['type'] == 'LONG':
            pnl = (exit_price - entry_price) / entry_price
        else:
            pnl = (entry_price - exit_price) / entry_price
        
        trade_result = {
            'symbol': symbol,
            'type': position['type'],
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'size': position['size']
        }
        
        self.trade_log.append(trade_result)
        self.capital *= (1 + pnl * self.config.POSITION_SIZE)
        
        logger.info(f"Closed {position['type']} position in {symbol} at {exit_price}. PnL: {pnl:.2%}")
        del self.positions[symbol]

    def get_trade_history(self) -> pd.DataFrame:
        """Return trade history as a DataFrame."""
        return pd.DataFrame(self.trade_log)

    def calculate_statistics(self) -> Dict:
        """Calculate trading statistics."""
        if not self.trade_log:
            return {}
            
        df = self.get_trade_history()
        
        stats = {
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl'] > 0]),
            'losing_trades': len(df[df['pnl'] <= 0]),
            'win_rate': len(df[df['pnl'] > 0]) / len(df) * 100,
            'avg_pnl': df['pnl'].mean() * 100,
            'max_drawdown': self.calculate_max_drawdown(df),
            'profit_factor': self.calculate_profit_factor(df),
            'final_capital': self.capital
        }
        
        return stats

    @staticmethod
    def calculate_max_drawdown(df: pd.DataFrame) -> float:
        """Calculate maximum drawdown from trade history."""
        cumulative_returns = (1 + df['pnl']).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        return abs(drawdowns.min()) * 100

    @staticmethod
    def calculate_profit_factor(df: pd.DataFrame) -> float:
        """Calculate profit factor from trade history."""
        winning_trades = df[df['pnl'] > 0]['pnl'].sum()
        losing_trades = abs(df[df['pnl'] < 0]['pnl'].sum())
        return winning_trades / losing_trades if losing_trades != 0 else float('inf') 