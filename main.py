#!/usr/bin/env python3
"""
CryptoPulse - AI-Powered Cryptocurrency Trading Bot

This is the main entry point for the CryptoPulse trading bot.
It orchestrates all the different modules and manages the application lifecycle.
"""

import asyncio
import sys
import os
from market_cap_tracker import update_market_cap_loop
from telegram_listener import TelegramListener
from utils import SignalHandler


class CryptoPulse:
    """Main application class that coordinates all components"""
    
    def __init__(self):
        self.signal_handler = SignalHandler()
        self.telegram_listener = TelegramListener()
        self.background_tasks = []
        
        # Register shutdown callbacks
        self.signal_handler.add_shutdown_callback(self._shutdown)
    
    async def start(self):
        """Start the CryptoPulse application"""
        try:
            print("🚀 Starting CryptoPulse Trading Bot...")
            print("=" * 50)
            
            # Start market cap tracker
            market_cap_task = asyncio.create_task(update_market_cap_loop())
            self.background_tasks.append(market_cap_task)
            print("✅ Market cap tracker started")
            
            # Start Telegram listener
            await self.telegram_listener.start()
            print("✅ Telegram listener started")
            
            print("=" * 50)
            print("🤖 CryptoPulse is now running!")
            print("Monitoring channels for crypto signals...")
            print("Press Ctrl+C to stop")
            print("=" * 50)
            
            # Keep running
            await self.telegram_listener.run_forever()
            
        except Exception as e:
            print(f"❌ Error starting CryptoPulse: {e}")
            await self._shutdown()
    
    async def _shutdown(self):
        """Gracefully shutdown all components"""
        try:
            print("\n🛑 Shutting down CryptoPulse...")
            
            # Stop Telegram listener
            await self.telegram_listener.stop()
            print("✅ Telegram listener stopped")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            print("✅ Background tasks stopped")
            
            print("✅ CryptoPulse shutdown completed")
            
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
    
    def get_status(self):
        """Get application status"""
        return {
            "listener_status": self.telegram_listener.get_status(),
            "background_tasks": len(self.background_tasks)
        }


async def main():
    """Main entry point"""
    try:
        # Check if running in development mode
        if len(sys.argv) > 1 and sys.argv[1] == "--dev":
            print("🔧 Running in development mode")
            os.environ['ENV'] = 'dev'
        
        # Create and start application
        app = CryptoPulse()
        await app.start()
        
    except KeyboardInterrupt:
        print("\n👋 CryptoPulse stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        sys.exit(1)