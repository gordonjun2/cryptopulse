#!/usr/bin/env python3
"""
Test script to verify the refactored CryptoPulse modules work correctly.
This performs basic import tests and simple functionality checks.
"""

import sys
import asyncio
import traceback
from typing import List, Tuple


def test_imports() -> Tuple[bool, List[str]]:
    """Test that all modules can be imported correctly"""
    modules_to_test = [
        'config',
        'utils',
        'data_manager',
        'market_cap_tracker',
        'binance_client',
        'llm_processor',
        'trading_engine',
        'telegram_bot',
        'telegram_listener',
        'main'
    ]
    
    results = []
    all_passed = True
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            results.append(f"✅ {module_name}")
        except ImportError as e:
            results.append(f"❌ {module_name}: {str(e)}")
            all_passed = False
        except Exception as e:
            results.append(f"⚠️  {module_name}: {str(e)}")
            all_passed = False
    
    return all_passed, results


async def test_data_manager():
    """Test basic data manager functionality"""
    try:
        from data_manager import DataManager
        
        dm = DataManager()
        
        # Test basic operations
        test_data = {"test_key": "test_value"}
        success = await dm.save_data(test_data, "test_file.json")
        
        if success:
            loaded_data = await dm.load_data("test_file.json")
            if loaded_data == test_data:
                return "✅ DataManager basic operations work"
            else:
                return "❌ DataManager: Data mismatch"
        else:
            return "❌ DataManager: Save operation failed"
    
    except Exception as e:
        return f"❌ DataManager: {str(e)}"


async def test_binance_client():
    """Test Binance client initialization"""
    try:
        from binance_client import BinanceClient
        
        client = BinanceClient()
        
        # Test symbol validation
        valid_symbol = client.is_valid_symbol("BTCUSDT")
        invalid_symbol = client.is_valid_symbol("INVALID")
        
        if valid_symbol and not invalid_symbol:
            return "✅ BinanceClient validation works"
        else:
            return "❌ BinanceClient: Symbol validation failed"
    
    except Exception as e:
        return f"❌ BinanceClient: {str(e)}"


async def test_llm_processor():
    """Test LLM processor initialization"""
    try:
        from llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        # Test response parsing
        test_response = """Coins: BTC, ETH
Sentiment: 75%

Explanation: Positive sentiment detected"""
        
        coins, sentiment, explanation = processor.parse_llm_response(test_response)
        
        if coins == ['BTC', 'ETH'] and sentiment == 75.0:
            return "✅ LLMProcessor parsing works"
        else:
            return "❌ LLMProcessor: Parsing failed"
    
    except Exception as e:
        return f"❌ LLMProcessor: {str(e)}"


async def test_utils():
    """Test utility functions"""
    try:
        from utils import format_currency, format_percentage, validate_symbol
        
        # Test formatting
        currency = format_currency(1234.56)
        percentage = format_percentage(12.34)
        
        # Test validation
        valid = validate_symbol("BTCUSDT")
        invalid = validate_symbol("INVALID")
        
        if currency == "$1,234.56" and percentage == "+12.34%" and valid and not invalid:
            return "✅ Utils functions work"
        else:
            return "❌ Utils: Function tests failed"
    
    except Exception as e:
        return f"❌ Utils: {str(e)}"


async def run_tests():
    """Run all tests"""
    print("🧪 Testing Refactored CryptoPulse Modules")
    print("=" * 50)
    
    # Test imports
    print("\n📦 Testing Module Imports:")
    import_success, import_results = test_imports()
    for result in import_results:
        print(f"  {result}")
    
    # Test functionality
    print("\n⚙️  Testing Module Functionality:")
    
    tests = [
        test_data_manager(),
        test_binance_client(),
        test_llm_processor(),
        test_utils()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"  ❌ Test failed: {str(result)}")
        else:
            print(f"  {result}")
    
    # Summary
    print("\n" + "=" * 50)
    if import_success:
        print("✅ All modules imported successfully!")
        print("🚀 The refactored codebase is ready to use!")
        print("\nNext steps:")
        print("1. Configure your API keys in private.ini")
        print("2. Run: python main.py")
        print("3. Or use the shell script: ./run_cryptopulse_script.sh")
    else:
        print("❌ Some modules failed to import")
        print("💡 Check the error messages above and install missing dependencies")
        print("   Run: pip install -r requirements.txt")


if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)