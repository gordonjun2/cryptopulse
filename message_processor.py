import re
import asyncio
import aiohttp
from config import TRADE_SENTIMENT_THRESHOLD, TOP_N_MARKETCAP, HODL_TIME
from market_cap_tracker import is_top_market_cap


class MessageProcessor:
    def __init__(self, llm_service, binance_client, queue_manager, use_bot=False):
        self.llm_service = llm_service
        self.binance_client = binance_client
        self.queue_manager = queue_manager
        self.use_bot = use_bot
        self.bot = None

    def set_bot(self, bot):
        """Set the bot instance for message replies"""
        self.bot = bot

    def extract_sentiment(self, content):
        """Extract sentiment from LLM response"""
        try:
            sentiment_match = re.search(r"Sentiment:\s*([-+]?\d+)%", content)
            sentiment = float(sentiment_match.group(1)) if sentiment_match else 0
        except (AttributeError, ValueError) as e:
            print(f"Error extracting sentiment: {e}", flush=True)
            sentiment = 0
        return sentiment

    def extract_symbols(self, content):
        """Extract symbols from LLM response"""
        try:
            matches = re.findall(r"Coins:\s*([\w, /]+)", content)
            symbols = matches[0].replace(" ", "").split(",") if matches else []
        except Exception as e:
            print(f"Error extracting symbols: {e}", flush=True)
            symbols = []
        return symbols

    async def send_error_message(self, forwarded_message, error_msg):
        """Send error message using appropriate bot"""
        print(error_msg, flush=True)
        if self.use_bot and self.bot:
            await self.bot.send_message(
                forwarded_message.chat.id,
                error_msg,
                reply_to_message_id=forwarded_message.id)
        else:
            await forwarded_message.reply_text(error_msg, quote=True)

    async def send_reply_message(self, forwarded_message, content):
        """Send reply message using appropriate bot"""
        if self.use_bot and self.bot:
            replied_message = await self.bot.send_message(
                forwarded_message.chat.id,
                content,
                reply_to_message_id=forwarded_message.id)
        else:
            replied_message = await forwarded_message.reply_text(content, quote=True)
        print(f"Replied with content:\n{content}\n")
        return replied_message

    async def process_trading_symbols(self, symbols, direction, replied_message, original_chat_id):
        """Process symbols for trading"""
        not_found_tickers = []
        
        for symbol in symbols:
            if symbol == 'N/A' or not symbol:
                continue
            if "USDT" not in symbol:
                symbol += "USDT"
            
            # Check if ticker can be traded in Binance
            if self.binance_client.is_symbol_available(symbol):
                # Check if symbol is in top market cap
                if is_top_market_cap(symbol):
                    text = f"{symbol} is in the top {TOP_N_MARKETCAP} market cap list, skipping trade...\n"
                    print(text, flush=True)
                    await replied_message.reply_text(text, quote=True)
                    continue

                # Check if symbol is already in queue or being processed
                if self.queue_manager.is_symbol_queued_or_processing(symbol):
                    text = f"{symbol} is already in queue or being processed for a trade, skipping...\n"
                    print(text, flush=True)
                    await replied_message.reply_text(text, quote=True)
                else:
                    text = f"Ticker {symbol} found in Binance API, hence a trade will be executed now. It will be closed in {HODL_TIME / 60:,.2f} minutes. \n"
                    print(text, flush=True)
                    trade_replied_message = await replied_message.reply_text(text, quote=True)
                    print(f"Adding {symbol} to the queue\n", flush=True)
                    
                    await self.queue_manager.add_to_queue(symbol, direction, trade_replied_message, original_chat_id)
            else:
                not_found_tickers.append(symbol)

        if not_found_tickers:
            not_found_tickers_string = ", ".join(not_found_tickers)
            text = f"Ticker(s) {not_found_tickers_string} not found in Binance API, hence no trade is executed.\n"
            print(text)
            await replied_message.reply_text(text, quote=True)

    async def process_message(self, session, forwarded_message, original_message):
        """Process a single message through LLM and handle trading logic"""
        try:
            message_text = forwarded_message.text or forwarded_message.caption
            
            content, error = await self.llm_service.analyze_sentiment(session, message_text)
            
            if error:
                await self.send_error_message(forwarded_message, error)
                return

            replied_message = await self.send_reply_message(forwarded_message, content)

            # Extract sentiment from the content
            sentiment = self.extract_sentiment(content)

            if abs(sentiment) >= TRADE_SENTIMENT_THRESHOLD:
                direction = "LONG" if sentiment > 0 else "SHORT"

                # Extract symbols from the content
                symbols = self.extract_symbols(content)

                await self.process_trading_symbols(symbols, direction, replied_message, original_message.chat.id)
            else:
                print("Trade sentiment is below the threshold, hence no trade is executed.\n")

        except Exception as e:
            error_msg = f"Error processing API response: {e}"
            await self.send_error_message(forwarded_message, error_msg)

    async def run_processor(self, message_queue):
        """Main processor loop"""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    forwarded_message, original_message = await message_queue.get()
                    await self.process_message(session, forwarded_message, original_message)
                except Exception as e:
                    print(f"Critical error in message processor: {e}\n", flush=True)
                finally:
                    message_queue.task_done()