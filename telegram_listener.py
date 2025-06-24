import asyncio
import re
from pyrogram import Client, utils, filters, idle
from llm_processor import LLMProcessor
from trading_engine import TradingEngine
from telegram_bot import TelegramBot
from config import (
    TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST, MAIN_CHAT_ID,
    TRADE_SENTIMENT_THRESHOLD
)


class TelegramListener:
    """Handles Telegram message monitoring and processing"""
    
    def __init__(self):
        # Monkey patch for Pyrogram
        utils.get_peer_type = self._get_peer_type
        
        self.app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)
        self.llm_processor = LLMProcessor()
        self.trading_engine = TradingEngine()
        self.telegram_bot = TelegramBot()
        self.message_queue = asyncio.Queue()
        
        # Register handlers
        self._register_handlers()
    
    def _get_peer_type(self, peer_id: int) -> str:
        """Monkey patch for Pyrogram peer type detection"""
        peer_id_str = str(peer_id)
        if not peer_id_str.startswith("-"):
            return "user"
        elif peer_id_str.startswith("-100"):
            return "channel"
        else:
            return "chat"
    
    def _register_handlers(self):
        """Register Pyrogram message handlers"""
        @self.app.on_message(filters.chat(CHAT_ID_LIST))
        async def message_handler(client, message):
            await self._handle_message(client, message)
    
    async def start(self):
        """Start the listener and related services"""
        try:
            # Start services
            await self.trading_engine.start_workers()
            await self.telegram_bot.setup()
            
            # Start message processor
            asyncio.create_task(self._message_processor())
            
            # Start Pyrogram client
            await self.app.start()
            print("Telegram listener started successfully")
            
        except Exception as e:
            print(f"Error starting Telegram listener: {e}")
    
    async def stop(self):
        """Stop the listener and cleanup"""
        try:
            await self.trading_engine.stop_workers()
            await self.telegram_bot.stop()
            await self.app.stop()
            print("Telegram listener stopped")
        except Exception as e:
            print(f"Error stopping Telegram listener: {e}")
    
    async def _handle_message(self, client, message):
        """Handle incoming messages from monitored chats"""
        try:
            # Skip messages without text or caption
            message_text = message.text or message.caption
            if not message_text:
                return
            
            print(f"\n📨 New message from {message.chat.title or message.chat.id}")
            print(f"Content: {message_text[:100]}...")
            
            # Forward message to main chat if it's not from main chat
            if message.chat.id != MAIN_CHAT_ID:
                try:
                    forwarded_message = await client.forward_messages(
                        chat_id=MAIN_CHAT_ID,
                        from_chat_id=message.chat.id,
                        message_ids=message.id
                    )
                    
                    # Queue for processing
                    await self.message_queue.put((forwarded_message[0], message))
                    
                except Exception as e:
                    print(f"Error forwarding message: {e}")
            else:
                # Queue for processing directly
                await self.message_queue.put((message, message))
                
        except Exception as e:
            print(f"Error handling message: {e}")
    
    async def _message_processor(self):
        """Process messages from the queue using LLM"""
        print("Message processor started")
        
        while True:
            try:
                forwarded_message, original_message = await self.message_queue.get()
                
                message_text = forwarded_message.text or forwarded_message.caption
                if not message_text:
                    continue
                
                print(f"\n🤖 Processing message with LLM...")
                
                # Analyze message with LLM
                coins, sentiment, explanation = await self.llm_processor.process_message(message_text)
                
                if not coins or sentiment is None:
                    print("No coins or sentiment detected, skipping")
                    continue
                
                print(f"Detected coins: {coins}")
                print(f"Sentiment: {sentiment}%")
                print(f"Explanation: {explanation}")
                
                # Check sentiment threshold
                abs_sentiment = abs(sentiment)
                if abs_sentiment < TRADE_SENTIMENT_THRESHOLD:
                    print(f"Sentiment {abs_sentiment}% below threshold {TRADE_SENTIMENT_THRESHOLD}%, skipping")
                    continue
                
                # Determine trading direction
                direction = "LONG" if sentiment > 0 else "SHORT"
                
                # Queue trades for each detected coin
                for coin in coins:
                    symbol = self._normalize_symbol(coin)
                    if symbol:
                        success = await self.trading_engine.queue_trade(
                            symbol, direction, forwarded_message, original_message.chat.id
                        )
                        if success:
                            print(f"✅ Queued {direction} trade for {symbol}")
                        else:
                            print(f"❌ Failed to queue trade for {symbol}")
                
                # Send analysis result via bot
                analysis_text = self._format_analysis_result(coins, sentiment, explanation)
                await self.telegram_bot.send_message(
                    forwarded_message.chat.id, 
                    analysis_text,
                    forwarded_message.id
                )
                
            except Exception as e:
                print(f"Error in message processor: {e}")
            finally:
                self.message_queue.task_done()
    
    def _normalize_symbol(self, coin: str) -> str:
        """Normalize coin symbol to USDT pair format"""
        try:
            # Clean the symbol
            symbol = re.sub(r'[^A-Za-z0-9]', '', coin.upper())
            
            # Add USDT if not present
            if not symbol.endswith('USDT'):
                symbol += 'USDT'
            
            return symbol
        except Exception as e:
            print(f"Error normalizing symbol {coin}: {e}")
            return ""
    
    def _format_analysis_result(self, coins: list, sentiment: float, explanation: str) -> str:
        """Format analysis result for display"""
        direction = "🟢 BULLISH" if sentiment > 0 else "🔴 BEARISH"
        coins_str = ", ".join(coins) if coins else "N/A"
        
        return f"""🤖 **AI Analysis Result**

**Detected Coins:** {coins_str}
**Sentiment:** {direction} ({sentiment:+.1f}%)
**Explanation:** {explanation}

Trades queued based on sentiment analysis."""
    
    async def run_forever(self):
        """Keep the listener running"""
        try:
            await idle()
        except Exception as e:
            print(f"Error in main loop: {e}")
    
    def get_status(self) -> dict:
        """Get listener status"""
        return {
            "is_connected": self.app.is_connected,
            "monitored_chats": len(CHAT_ID_LIST),
            "message_queue_size": self.message_queue.qsize(),
            "trading_queue_status": self.trading_engine.get_queue_status()
        }