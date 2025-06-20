"""
Optimized Trading Engine for CryptoPulse Bot
Demonstrates improved architecture, error handling, and async patterns
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
from binance.client import Client
from binance.exceptions import BinanceAPIException


# Custom exceptions for better error handling
class TradingError(Exception):
    """Base exception for trading operations"""
    pass


class InsufficientFundsError(TradingError):
    pass


class InvalidSymbolError(TradingError):
    pass


class APIRateLimitError(TradingError):
    pass


class PositionAlreadyActiveError(TradingError):
    pass


@dataclass
class TradeResult:
    """Structured trade result"""
    success: bool
    symbol: str
    direction: str
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    error_message: str = ""
    trade_duration: float = 0.0


@dataclass
class TradingConfig:
    """Trading configuration"""
    initial_capital: float = 3000
    leverage: int = 1
    hodl_time: int = 300
    max_daily_trades: int = 50
    max_position_size: float = 10000
    ssl_verify: bool = True


def handle_binance_exceptions(func):
    """Decorator for handling Binance API exceptions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BinanceAPIException as e:
            if e.code == -2019:  # Insufficient balance
                raise InsufficientFundsError(f"Insufficient funds: {e.message}")
            elif e.code == -1121:  # Invalid symbol
                raise InvalidSymbolError(f"Invalid symbol: {e.message}")
            elif e.code == -1003:  # Rate limit
                raise APIRateLimitError(f"Rate limit exceeded: {e.message}")
            else:
                raise TradingError(f"Binance API error: {e.message}")
        except Exception as e:
            logging.exception(f"Unexpected error in {func.__name__}")
            raise TradingError(f"Unexpected error: {str(e)}")
    return wrapper


def async_retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (APIRateLimitError, TradingError) as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Don't retry on unexpected errors
                    raise
            
            return None
        return wrapper
    return decorator


class SymbolPrecisionCache:
    """Cache for symbol precision data with TTL"""
    
    def __init__(self, ttl_seconds=3600):
        self._cache = {}
        self._cache_time = {}
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
    
    async def get_precision(self, symbol: str, client: Client) -> Optional[int]:
        """Get precision for a symbol, refreshing cache if needed"""
        async with self._lock:
            now = time.time()
            if (symbol in self._cache and 
                now - self._cache_time.get(symbol, 0) < self._ttl):
                return self._cache[symbol]
            
            # Refresh cache for this symbol
            await self._refresh_cache(client)
            return self._cache.get(symbol)
    
    async def _refresh_cache(self, client: Client):
        """Refresh the entire precision cache"""
        try:
            loop = asyncio.get_event_loop()
            exchange_info = await loop.run_in_executor(None, client.futures_exchange_info)
            
            for symbol_info in exchange_info["symbols"]:
                symbol = symbol_info.get("symbol")
                precision = symbol_info.get("quantityPrecision")
                if symbol and precision is not None:
                    self._cache[symbol] = int(precision)
                    self._cache_time[symbol] = time.time()
                    
        except Exception as e:
            logging.error(f"Failed to refresh precision cache: {e}")


class OptimizedTradingEngine:
    """
    Optimized trading engine with proper async patterns, error handling,
    and resource management
    """
    
    def __init__(self, client: Client, config: TradingConfig):
        self.client = client
        self.config = config
        self.active_positions = {}
        self.position_lock = asyncio.Lock()
        self.precision_cache = SymbolPrecisionCache()
        self.daily_trades = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def can_trade(self, symbol: str) -> Tuple[bool, str]:
        """Check if we can trade this symbol"""
        # Check daily limits
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self.last_reset_date:
            self.daily_trades = 0
            self.last_reset_date = current_date
        
        if self.daily_trades >= self.config.max_daily_trades:
            return False, "Daily trade limit reached"
        
        # Check if position already active
        async with self.position_lock:
            if symbol in self.active_positions:
                return False, f"Position already active for {symbol}"
        
        return True, "OK"
    
    @handle_binance_exceptions
    @async_retry_with_backoff(max_retries=3, base_delay=1, max_delay=30)
    async def execute_trade(self, symbol: str, direction: str) -> TradeResult:
        """
        Execute a complete trade cycle with proper error handling
        """
        start_time = time.time()
        
        # Pre-trade validation
        can_trade, reason = await self.can_trade(symbol)
        if not can_trade:
            return TradeResult(
                success=False,
                symbol=symbol,
                direction=direction,
                error_message=reason
            )
        
        try:
            # Mark position as active
            async with self.position_lock:
                self.active_positions[symbol] = {
                    "direction": direction,
                    "start_time": start_time
                }
            
            # Execute entry
            entry_result = await self._enter_position(symbol, direction)
            if not entry_result["success"]:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    direction=direction,
                    error_message=entry_result["error"]
                )
            
            # Wait for hold time
            await asyncio.sleep(self.config.hodl_time)
            
            # Execute exit
            exit_result = await self._exit_position(symbol, direction, entry_result["quantity"])
            if not exit_result["success"]:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_result["price"],
                    quantity=entry_result["quantity"],
                    error_message=exit_result["error"]
                )
            
            # Calculate P&L
            pnl = self._calculate_pnl(
                entry_result["price"], 
                exit_result["price"], 
                entry_result["quantity"], 
                direction
            )
            
            # Update trade count
            self.daily_trades += 1
            
            trade_duration = time.time() - start_time
            
            self.logger.info(
                f"Trade completed: {symbol} {direction} "
                f"Entry: ${entry_result['price']:.4f} "
                f"Exit: ${exit_result['price']:.4f} "
                f"P&L: ${pnl:.2f} "
                f"Duration: {trade_duration:.1f}s"
            )
            
            return TradeResult(
                success=True,
                symbol=symbol,
                direction=direction,
                entry_price=entry_result["price"],
                exit_price=exit_result["price"],
                quantity=entry_result["quantity"],
                pnl=pnl,
                trade_duration=trade_duration
            )
            
        except Exception as e:
            self.logger.error(f"Trade execution failed for {symbol}: {e}")
            return TradeResult(
                success=False,
                symbol=symbol,
                direction=direction,
                error_message=str(e)
            )
        
        finally:
            # Clean up position tracking
            async with self.position_lock:
                self.active_positions.pop(symbol, None)
    
    async def _enter_position(self, symbol: str, direction: str) -> Dict:
        """Enter a trading position"""
        try:
            # Get current price
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                None, self.client.futures_symbol_ticker, symbol
            )
            price = float(ticker["price"])
            
            # Get symbol precision
            precision = await self.precision_cache.get_precision(symbol, self.client)
            if precision is None:
                return {"success": False, "error": "Could not get symbol precision"}
            
            # Calculate order size
            order_size = (self.config.initial_capital * self.config.leverage) / price
            
            # Round to proper precision
            order_size = round(order_size, precision)
            
            # Validate order size
            if order_size * price > self.config.max_position_size:
                return {"success": False, "error": "Position size exceeds maximum"}
            
            # Set leverage
            await loop.run_in_executor(
                None, self.client.futures_change_leverage, symbol, self.config.leverage
            )
            
            # Place order
            side = "BUY" if direction == "LONG" else "SELL"
            order = await loop.run_in_executor(
                None, self.client.futures_create_order,
                symbol, side, "MARKET", order_size
            )
            
            if order:
                return {
                    "success": True,
                    "price": price,
                    "quantity": order_size,
                    "order_id": order.get("orderId")
                }
            else:
                return {"success": False, "error": "Order placement failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _exit_position(self, symbol: str, direction: str, quantity: float) -> Dict:
        """Exit a trading position"""
        try:
            # Get current price
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(
                None, self.client.futures_symbol_ticker, symbol
            )
            price = float(ticker["price"])
            
            # Place opposite order
            side = "SELL" if direction == "LONG" else "BUY"
            order = await loop.run_in_executor(
                None, self.client.futures_create_order,
                symbol, side, "MARKET", quantity
            )
            
            if order:
                return {
                    "success": True,
                    "price": price,
                    "order_id": order.get("orderId")
                }
            else:
                return {"success": False, "error": "Exit order failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_pnl(self, entry_price: float, exit_price: float, 
                      quantity: float, direction: str) -> float:
        """Calculate profit/loss for a trade"""
        if direction == "LONG":
            return (exit_price - entry_price) * quantity
        else:  # SHORT
            return (entry_price - exit_price) * quantity
    
    async def get_active_positions(self) -> Dict:
        """Get currently active positions"""
        async with self.position_lock:
            return self.active_positions.copy()
    
    async def force_close_position(self, symbol: str) -> bool:
        """Force close a position (emergency stop)"""
        async with self.position_lock:
            if symbol not in self.active_positions:
                return False
            
            position = self.active_positions[symbol]
            # Implementation for emergency close
            # This would need to query current position and close it
            
            return True
    
    async def cleanup(self):
        """Cleanup resources"""
        # Close any remaining positions
        active = await self.get_active_positions()
        for symbol in active:
            self.logger.warning(f"Force closing position for {symbol}")
            await self.force_close_position(symbol)


# Example usage
async def main():
    """Example usage of the optimized trading engine"""
    from binance.client import Client
    
    # Initialize client (use testnet for safety)
    client = Client("your_api_key", "your_secret", testnet=True)
    
    # Configure trading parameters
    config = TradingConfig(
        initial_capital=1000,
        leverage=1,
        hodl_time=300,  # 5 minutes
        max_daily_trades=10
    )
    
    # Create trading engine
    engine = OptimizedTradingEngine(client, config)
    
    try:
        # Execute a trade
        result = await engine.execute_trade("BTCUSDT", "LONG")
        
        if result.success:
            print(f"Trade successful! P&L: ${result.pnl:.2f}")
        else:
            print(f"Trade failed: {result.error_message}")
            
    finally:
        # Always cleanup
        await engine.cleanup()


if __name__ == "__main__":
    asyncio.run(main())