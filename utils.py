import signal
import asyncio
from typing import Callable, Any


class SignalHandler:
    """Handle system signals for graceful shutdown"""
    
    def __init__(self):
        self.shutdown_callbacks = []
        self.setup_signal_handlers()
    
    def add_shutdown_callback(self, callback: Callable):
        """Add a callback to be called on shutdown"""
        self.shutdown_callbacks.append(callback)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print(f"\n🛑 Received signal {sig}, initiating graceful shutdown...")
            asyncio.create_task(self._shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _shutdown(self):
        """Execute all shutdown callbacks"""
        print("Executing shutdown callbacks...")
        
        for callback in self.shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                print(f"Error in shutdown callback: {e}")
        
        print("Graceful shutdown completed")
        exit(0)


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format currency amount with proper symbol and commas"""
    return f"{symbol}{amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format percentage with proper sign"""
    return f"{value:+.2f}%"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string if it exceeds max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to int with default fallback"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


async def retry_async_operation(
    operation: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    *args,
    **kwargs
) -> Any:
    """Retry an async operation with configurable backoff"""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt) if exponential_backoff else delay
                print(f"Operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                print(f"Operation failed after {max_retries} attempts")
    
    if last_exception:
        raise last_exception


def validate_symbol(symbol: str) -> bool:
    """Validate if symbol format is correct"""
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Basic validation - should be alphanumeric and end with USDT
    if not symbol.isalnum() or not symbol.endswith('USDT'):
        return False
    
    # Should have reasonable length
    if len(symbol) < 4 or len(symbol) > 20:
        return False
    
    return True


def sanitize_chat_name(name: str, max_length: int = 20) -> str:
    """Sanitize chat name for display"""
    if not name:
        return "Unknown"
    
    # Remove unwanted characters
    sanitized = ''.join(c for c in name if c.isalnum() or c in ' -_')
    
    # Truncate if too long
    return truncate_string(sanitized.strip(), max_length)