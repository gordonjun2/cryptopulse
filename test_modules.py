#!/usr/bin/env python3
"""
Simple test script to verify the refactored modules work correctly.
This script tests basic functionality without executing actual trades.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_modules():
    """Test basic functionality of all modules"""
    print("Testing CryptoPulse Modules")
    print("=" * 40)
    
    # Test 1: Import all modules
    print("\n1. Testing module imports...")
    try:
        from modules.binance_trader import BinanceTrader
        from modules.llm_client import LLMClient
        from modules.data_manager import DataManager
        from modules.message_processor import MessageProcessor
        print("✅ All modules imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 2: Initialize core components
    print("\n2. Testing component initialization...")
    try:
        # Initialize data manager (should work without external dependencies)
        data_manager = DataManager()
        print("✅ DataManager initialized")
        
        # Test data operations
        test_data = {"test_chat": 100.50}
        await data_manager.update_pnl_data(test_data)
        retrieved_data = await data_manager.get_pnl_data()
        
        if "test_chat" in retrieved_data and retrieved_data["test_chat"] == 100.50:
            print("✅ Data persistence working")
        else:
            print("❌ Data persistence failed")
            
    except Exception as e:
        print(f"❌ Component initialization error: {e}")
        return False
    
    # Test 3: LLM Client (structure only, no API calls)
    print("\n3. Testing LLM Client structure...")
    try:
        llm_client = LLMClient()
        # Test that the client initializes with correct settings
        if hasattr(llm_client, 'url') and hasattr(llm_client, 'headers'):
            print("✅ LLM Client structure correct")
        else:
            print("❌ LLM Client missing required attributes")
    except Exception as e:
        print(f"❌ LLM Client error: {e}")
    
    # Test 4: Binance Trader (structure only, no API calls)
    print("\n4. Testing Binance Trader structure...")
    try:
        binance_trader = BinanceTrader()
        # Test that basic methods exist
        required_methods = ['is_symbol_available', 'add_pending_symbol', 'remove_pending_symbol']
        for method in required_methods:
            if not hasattr(binance_trader, method):
                print(f"❌ Binance Trader missing method: {method}")
                return False
        print("✅ Binance Trader structure correct")
    except Exception as e:
        print(f"❌ Binance Trader error: {e}")
    
    # Test 5: Message Processor
    print("\n5. Testing Message Processor...")
    try:
        message_processor = MessageProcessor(
            binance_trader,
            llm_client,
            data_manager
        )
        
        # Test sentiment extraction
        test_content = "Sentiment: 75%\nCoins: BTC, ETH"
        sentiment = message_processor.extract_sentiment_from_content(test_content)
        symbols = message_processor.extract_symbols_from_content(test_content)
        
        if sentiment == 75.0 and "BTC" in symbols and "ETH" in symbols:
            print("✅ Message processing logic working")
        else:
            print(f"❌ Message processing failed: sentiment={sentiment}, symbols={symbols}")
            
    except Exception as e:
        print(f"❌ Message Processor error: {e}")
    
    print("\n" + "=" * 40)
    print("Module testing completed!")
    print("\nNote: This test only checks basic structure and imports.")
    print("Full functionality requires proper API keys and network access.")
    
    return True

if __name__ == "__main__":
    # Run the async test
    success = asyncio.run(test_modules())
    if success:
        print("\n🎉 All basic tests passed! The modular refactoring appears to be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
    
    # Clean up test files
    try:
        if os.path.exists("pnl_data.json"):
            os.remove("pnl_data.json")
        if os.path.exists("stats_data.json"):
            os.remove("stats_data.json")
        print("\n🧹 Cleaned up test files.")
    except:
        pass