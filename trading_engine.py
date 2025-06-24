import asyncio
import textwrap
from typing import Optional
from binance_client import BinanceClient
from data_manager import DataManager
from market_cap_tracker import is_top_market_cap
from config import (
    INITIAL_CAPITAL, LEVERAGE, HODL_TIME, BINANCE_TESTNET_FLAG, NUM_WORKERS
)


class TradingEngine:
    """Handles trading operations and queue management"""
    
    def __init__(self):
        self.binance_client = BinanceClient()
        self.data_manager = DataManager()
        self.symbol_queue = asyncio.Queue()
        self.processing_symbols = set()
        self.pending_symbols = set()
        self.workers = []
    
    async def start_workers(self):
        """Start worker tasks for processing trades"""
        self.workers = [
            asyncio.create_task(self._worker(f"Worker-{i}"))
            for i in range(NUM_WORKERS)
        ]
        print(f"Started {NUM_WORKERS} trading workers")
    
    async def stop_workers(self):
        """Stop all worker tasks"""
        # Send stop signals
        for _ in self.workers:
            await self.symbol_queue.put(None)
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        print("All trading workers stopped")
    
    async def _worker(self, worker_name: str):
        """Worker function to process trades from queue"""
        print(f"{worker_name} started")
        
        while True:
            try:
                item = await self.symbol_queue.get()
                
                if item is None:  # Stop signal
                    break
                
                symbol, direction, message, original_chat_id = item
                
                # Remove from pending and add to processing
                self.pending_symbols.discard(symbol)
                self.processing_symbols.add(symbol)
                
                # Execute trade
                await self._execute_trade(symbol, direction, message, original_chat_id)
                
            except Exception as e:
                print(f"Error in {worker_name}: {e}")
            finally:
                self.symbol_queue.task_done()
        
        print(f"{worker_name} stopped")
    
    async def queue_trade(self, symbol: str, direction: str, message, original_chat_id: str) -> bool:
        """Queue a trade for processing"""
        try:
            # Check if symbol is already being processed or pending
            if symbol in self.processing_symbols or symbol in self.pending_symbols:
                print(f"Trade for {symbol} already in progress, skipping")
                return False
            
            # Validate symbol
            if not self.binance_client.is_valid_symbol(symbol):
                print(f"Invalid symbol: {symbol}")
                return False
            
            # Check if symbol is in top market cap
            if not is_top_market_cap(symbol):
                print(f"Symbol {symbol} not in top market cap, skipping")
                return False
            
            # Add to pending and queue
            self.pending_symbols.add(symbol)
            await self.symbol_queue.put((symbol, direction, message, original_chat_id))
            
            print(f"Queued trade: {symbol} {direction}")
            return True
            
        except Exception as e:
            print(f"Error queuing trade: {e}")
            return False
    
    async def _execute_trade(self, symbol: str, direction: str, message, original_chat_id: str):
        """Execute a single trade"""
        try:
            base_symbol = symbol.replace("USDT", "")
            
            print(f"\nExecuting Trade:")
            print(f"Symbol: {symbol}")
            print(f"Direction: {direction}")
            print(f"Capital: ${INITIAL_CAPITAL:,.2f}")
            print(f"Leverage: {LEVERAGE}x")
            
            # Get current price
            ticker = self.binance_client.get_price(symbol)
            if not ticker:
                await self._send_error_message(message, f"Failed to get price for {symbol}")
                return
            
            try:
                price = float(ticker["price"])
            except (KeyError, ValueError) as e:
                await self._send_error_message(message, f"Invalid price data for {symbol}: {e}")
                return
            
            # Calculate order size
            order_size = self.binance_client.calculate_order_size(
                symbol, price, INITIAL_CAPITAL, LEVERAGE
            )
            
            if not order_size:
                await self._send_error_message(message, f"Failed to calculate order size for {symbol}")
                return
            
            # Set leverage if using testnet
            if BINANCE_TESTNET_FLAG:
                self.binance_client.change_leverage(symbol, LEVERAGE)
            
            # Place entry order
            if direction == 'LONG':
                entry_order = self.binance_client.place_buy_order(symbol, order_size)
            else:
                entry_order = self.binance_client.place_sell_order(symbol, order_size)
            
            if not entry_order and BINANCE_TESTNET_FLAG:
                await self._send_error_message(message, f"Failed to place entry order for {symbol}")
                return
            
            print(f"Entry order executed: {order_size:,.4f} {base_symbol} at ${price}")
            
            # Hold position
            await asyncio.sleep(HODL_TIME)
            print(f"Held position for {HODL_TIME} seconds")
            
            # Get exit price
            exit_ticker = self.binance_client.get_price(symbol)
            if not exit_ticker:
                await self._send_error_message(message, f"Failed to get exit price for {symbol}")
                return
            
            try:
                exit_price = float(exit_ticker["price"])
            except (KeyError, ValueError) as e:
                await self._send_error_message(message, f"Invalid exit price data for {symbol}: {e}")
                return
            
            # Place exit order
            if direction == 'LONG':
                exit_order = self.binance_client.place_sell_order(symbol, order_size)
            else:
                exit_order = self.binance_client.place_buy_order(symbol, order_size)
            
            if not exit_order and BINANCE_TESTNET_FLAG:
                await self._send_error_message(message, f"Failed to place exit order for {symbol}")
                return
            
            print(f"Exit order executed: {order_size:,.4f} {base_symbol} at ${exit_price}")
            
            # Calculate P&L
            pnl = self._calculate_pnl(direction, order_size, price, exit_price, INITIAL_CAPITAL)
            percentage_pnl = (pnl / INITIAL_CAPITAL) * 100
            
            print(f"Trade completed: P&L = ${pnl:,.2f} ({percentage_pnl:+.2f}%)")
            
            # Update data
            await self.data_manager.update_pnl_data({str(original_chat_id): pnl})
            await self.data_manager.update_stats_data(pnl)
            
            # Send success message
            await self._send_trade_result(
                message, symbol, direction, order_size, base_symbol, 
                price, exit_price, INITIAL_CAPITAL, pnl, percentage_pnl
            )
            
        except Exception as e:
            print(f"Critical error in trade execution: {e}")
            await self._send_error_message(message, f"Trade execution failed: {e}")
        finally:
            self.processing_symbols.discard(symbol)
    
    def _calculate_pnl(self, direction: str, quantity: float, entry_price: float, 
                      exit_price: float, capital: float) -> float:
        """Calculate profit/loss for a trade"""
        try:
            if direction == 'LONG':
                return (exit_price - entry_price) * quantity
            else:  # SHORT
                return (entry_price - exit_price) * quantity
        except Exception as e:
            print(f"Error calculating P&L: {e}")
            return 0.0
    
    async def _send_trade_result(self, message, symbol: str, direction: str, 
                               quantity: float, base_symbol: str, entry_price: float,
                               exit_price: float, capital: float, pnl: float, 
                               percentage_pnl: float):
        """Send trade result message"""
        try:
            content = textwrap.dedent(f"""\
            🚀 **{direction} Trade Completed** 🚀

            **Trading Parameters:**
            __Symbol:__ {symbol}  
            __Order Size (in USDT):__ ${capital * LEVERAGE:,.2f}  

            **Entry Order:**  
            {quantity:,.4f} {base_symbol} at ${entry_price}  

            **Exit Order ({HODL_TIME / 60:,.1f} mins later):**  
            {quantity:,.4f} {base_symbol} at ${exit_price}  

            **Trade Summary:**  
            __Capital:__ ${capital:.2f}  
            __P&L:__ ${pnl:.2f} ({percentage_pnl:+.2f}%)
            """)
            
            await message.reply_text(content, quote=True)
        except Exception as e:
            print(f"Error sending trade result: {e}")
    
    async def _send_error_message(self, message, error_text: str):
        """Send error message"""
        try:
            await message.reply_text(f"❌ Error: {error_text}", quote=True)
        except Exception as e:
            print(f"Error sending error message: {e}")
    
    def get_queue_status(self) -> dict:
        """Get current queue status"""
        return {
            "pending_symbols": len(self.pending_symbols),
            "processing_symbols": len(self.processing_symbols),
            "queue_size": self.symbol_queue.qsize()
        }