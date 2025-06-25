import re
import asyncio
from config import (TRADE_SENTIMENT_THRESHOLD, HODL_TIME, TOP_N_MARKETCAP)
from market_cap_tracker import is_top_market_cap


class MessageProcessor:
    """Handles message processing, sentiment analysis, and trading decisions"""
    
    def __init__(self, binance_trader, llm_client, data_manager, use_bot=False):
        self.binance_trader = binance_trader
        self.llm_client = llm_client
        self.data_manager = data_manager
        self.use_bot = use_bot
        self.message_queue = asyncio.Queue()
        self.symbol_queue = asyncio.Queue()
    
    async def add_message_to_queue(self, forwarded_message, original_message):
        """Add message to processing queue"""
        await self.message_queue.put((forwarded_message, original_message))
    
    async def add_symbol_to_queue(self, symbol, direction, message, original_chat_id):
        """Add symbol to trading queue"""
        await self.symbol_queue.put((symbol, direction, message, original_chat_id))
    
    def extract_sentiment_from_content(self, content):
        """Extract sentiment percentage from LLM response"""
        try:
            sentiment_match = re.search(r"Sentiment:\s*([-+]?\d+)%", content)
            sentiment = float(sentiment_match.group(1)) if sentiment_match else 0
        except (AttributeError, ValueError) as e:
            print(f"Error extracting sentiment: {e}", flush=True)
            sentiment = 0
        return sentiment
    
    def extract_symbols_from_content(self, content):
        """Extract trading symbols from LLM response"""
        try:
            matches = re.findall(r"Coins:\s*([\w, /]+)", content)
            symbols = matches[0].replace(" ", "").split(",") if matches else []
        except Exception as e:
            print(f"Error extracting symbols: {e}", flush=True)
            symbols = []
        return symbols
    
    async def process_trading_decision(self, content, replied_message):
        """Process trading decision based on LLM response"""
        sentiment = self.extract_sentiment_from_content(content)
        
        if abs(sentiment) >= TRADE_SENTIMENT_THRESHOLD:
            direction = "LONG" if sentiment > 0 else "SHORT"
            symbols = self.extract_symbols_from_content(content)
            
            not_found_tickers = []
            for symbol in symbols:
                if symbol == 'N/A' or not symbol:
                    continue
                if "USDT" not in symbol:
                    symbol += "USDT"
                
                # Check if ticker can be traded in Binance
                if self.binance_trader.is_symbol_available(symbol):
                    # Check if symbol is in top market cap
                    if is_top_market_cap(symbol):
                        text = f"{symbol} is in the top {TOP_N_MARKETCAP} market cap list, skipping trade...\n"
                        print(text, flush=True)
                        await replied_message.reply_text(text, quote=True)
                        continue

                    # Check if symbol is already in queue or being processed
                    if self.binance_trader.is_symbol_in_queue_or_processing(symbol):
                        text = f"{symbol} is already in queue or being processed for a trade, skipping...\n"
                        print(text, flush=True)
                        await replied_message.reply_text(text, quote=True)
                    else:
                        text = f"Ticker {symbol} found in Binance API, hence a trade will be executed now. It will be closed in {HODL_TIME / 60:,.2f} minutes. \n"
                        print(text, flush=True)
                        trade_replied_message = await replied_message.reply_text(text, quote=True)
                        print(f"Adding {symbol} to the queue\n", flush=True)
                        
                        self.binance_trader.add_pending_symbol(symbol)
                        await self.add_symbol_to_queue(symbol, direction, trade_replied_message, replied_message.chat.id)
                else:
                    not_found_tickers.append(symbol)

            if not_found_tickers:
                not_found_tickers_string = ", ".join(not_found_tickers)
                text = f"Ticker(s) {not_found_tickers_string} not found in Binance API, hence no trade is executed.\n"
                print(text)
                await replied_message.reply_text(text, quote=True)
        else:
            print("Trade sentiment is below the threshold, hence no trade is executed.\n")
    
    async def send_bot_message_or_reply(self, message, content, bot=None):
        """Send message using bot or reply directly"""
        if self.use_bot and bot:
            return await bot.send_message(
                message.chat.id,
                content,
                reply_to_message_id=message.id
            )
        else:
            return await message.reply_text(content, quote=True)
    
    async def handle_llm_error(self, message, error_msg, bot=None):
        """Handle LLM API errors"""
        print(error_msg, flush=True)
        if self.use_bot and bot:
            await bot.send_message(
                message.chat.id,
                error_msg,
                reply_to_message_id=message.id
            )
        else:
            await message.reply_text(error_msg, quote=True)
    
    async def process_message(self, forwarded_message, original_message, bot=None):
        """Process a single message through LLM and handle trading decisions"""
        try:
            message_text = forwarded_message.text or forwarded_message.caption
            success, content, error_msg = await self.llm_client.get_llm_response(message_text)
            
            if not success:
                await self.handle_llm_error(forwarded_message, error_msg, bot)
                return
            
            replied_message = await self.send_bot_message_or_reply(forwarded_message, content, bot)
            print(f"Replied with content:\n{content}\n")
            
            # Process trading decision
            await self.process_trading_decision(content, replied_message)
            
        except Exception as e:
            error_msg = f"Critical error in message processor: {e}"
            print(error_msg + "\n", flush=True)
            await self.handle_llm_error(forwarded_message, error_msg, bot)
    
    async def message_processor_worker(self, bot=None):
        """Worker to process messages from the queue"""
        while True:
            try:
                forwarded_message, original_message = await self.message_queue.get()
                await self.process_message(forwarded_message, original_message, bot)
            except Exception as e:
                print(f"Critical error in message processor: {e}\n", flush=True)
            finally:
                self.message_queue.task_done()
    
    async def trading_worker(self):
        """Worker function to process tickers from the queue asynchronously"""
        while True:
            item = await self.symbol_queue.get()
            if item is None:
                break

            symbol, direction, message, original_chat_id = item

            # Remove from pending and add to processing
            self.binance_trader.remove_pending_symbol(symbol)
            self.binance_trader.add_processing_symbol(symbol)

            # Execute trade with callbacks for data updates
            await self.binance_trader.execute_trade(
                symbol, direction, message, original_chat_id,
                self.data_manager.update_pnl_data,
                self.data_manager.update_stats_data
            )

            self.symbol_queue.task_done()