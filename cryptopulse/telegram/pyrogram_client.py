"""
Pyrogram client for monitoring Telegram channels.
"""

import asyncio
import re
from pyrogram import Client, utils, filters, idle
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST, 
                   TRADE_SENTIMENT_THRESHOLD, TOP_N_MARKETCAP)
from market_cap_tracker import is_top_market_cap
from cryptopulse.core.llm_client import message_queue
from cryptopulse.core.trading import symbol_queue, processing_symbols, pending_symbols


def get_peer_type(peer_id: int) -> str:
    """Monkey patch for Pyrogram peer type detection."""
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"


# Apply monkey patch
utils.get_peer_type = get_peer_type


class PyrogramClient:
    """Manages Pyrogram client for Telegram message monitoring."""
    
    def __init__(self):
        self.app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up message handlers."""
        @self.app.on_message(filters.chat(CHAT_ID_LIST))
        async def message_handler(client, message):
            await self._handle_message(client, message)
    
    async def _handle_message(self, client, message):
        """Handle incoming messages from monitored channels."""
        try:
            # Add message to LLM processing queue
            await message_queue.put((message, message))
            
            # Process LLM response and extract trading signals
            # This logic would be implemented based on the original code
            # For now, we'll just log the message
            print(f"Received message from {message.chat.title}: {message.text[:100]}...")
            
        except Exception as e:
            print(f"Error handling message: {e}", flush=True)
    
    async def start(self):
        """Start the Pyrogram client."""
        await self.app.start()
    
    async def stop(self):
        """Stop the Pyrogram client."""
        await self.app.stop()
    
    async def run(self, main_func):
        """Run the client with the main function."""
        return await self.app.run(main_func)