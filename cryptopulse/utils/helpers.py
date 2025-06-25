"""
Helper utilities for CryptoPulse trading bot.
"""

import signal
import sys


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print("\nStopping the application...")
        print("The application has stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)  # SIGINT for Ctrl + C
    signal.signal(signal.SIGTSTP, signal_handler)  # SIGTSTP for Ctrl + Z


async def get_chat_id_name_dict(app, chat_id_list):
    """Get chat ID to name mapping dictionary."""
    chat_id_name_dict = {}
    for chat_id in chat_id_list:
        chat_id_str = str(chat_id)
        try:
            chat_info = await app.get_chat(chat_id)
            chat_id_name_dict[chat_id_str] = chat_info.title
        except Exception as e:
            print(f"Error getting chat info for {chat_id}: {e}")
            chat_id_name_dict[chat_id_str] = chat_id_str
    return chat_id_name_dict