#!/usr/bin/env python3
"""
CryptoPulse Trading Bot - Main Entry Point

This is the refactored main entry point that integrates all modular components.
All original functionality is preserved while organizing code into clean modules.
"""

import asyncio
import os
import sys

# Add the cryptopulse package to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (CHAT_ID_LIST, NUM_WORKERS)
from market_cap_tracker import update_market_cap_loop
from cryptopulse.core.trading import worker
from cryptopulse.core.llm_client import message_processor
from cryptopulse.telegram.pyrogram_client import PyrogramClient
from cryptopulse.telegram.aiogram_client import AiogramBotManager
from cryptopulse.telegram.handlers import CommandHandlers, set_commands
from cryptopulse.utils.helpers import setup_signal_handlers, get_chat_id_name_dict


async def main():
    """Main application entry point."""
    print("🚀 Starting CryptoPulse Trading Bot...")
    print("=" * 50)
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Initialize components
    pyrogram_client = PyrogramClient()
    aiogram_bot = AiogramBotManager()
    
    # Start Pyrogram client
    await pyrogram_client.start()
    
    # Check bot membership
    bot_membership_ok = await aiogram_bot.check_bot_membership()
    if not bot_membership_ok:
        return
    
    # Get chat ID to name mapping
    chat_id_name_dict = await get_chat_id_name_dict(pyrogram_client.app, CHAT_ID_LIST)
    
    # Set up command handlers
    handlers = CommandHandlers(aiogram_bot.router, chat_id_name_dict)
    
    # Set bot commands
    await set_commands(aiogram_bot.bot)
    
    # Create worker tasks
    print(f"Creating {NUM_WORKERS} worker tasks...")
    workers = [asyncio.create_task(worker()) for _ in range(NUM_WORKERS)]
    
    # Create other background tasks
    tasks = [
        asyncio.create_task(message_processor(aiogram_bot.use_bot, aiogram_bot.bot)),
        asyncio.create_task(update_market_cap_loop()),
        asyncio.create_task(aiogram_bot.start_polling()),
    ]
    
    print("✅ All components initialized successfully!")
    print("🔄 Bot is now running and monitoring channels...")
    print("Press Ctrl+C to stop the bot")
    print("=" * 50)
    
    try:
        # Run all tasks concurrently
        await asyncio.gather(*workers, *tasks)
    except KeyboardInterrupt:
        print("\n⚠️  Received interrupt signal. Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Clean shutdown
        print("🔄 Stopping workers...")
        
        # Stop worker tasks
        for _ in range(NUM_WORKERS):
            await symbol_queue.put(None)
        
        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Stop Pyrogram client
        await pyrogram_client.stop()
        
        # Close aiogram bot session
        if aiogram_bot.bot:
            await aiogram_bot.bot.session.close()
        
        print("✅ Shutdown complete!")


if __name__ == "__main__":
    try:
        # Import the symbol_queue here to avoid circular imports
        from cryptopulse.core.trading import symbol_queue
        
        # Run with Pyrogram's app.run() method
        pyrogram_client = PyrogramClient()
        pyrogram_client.app.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)