"""
Secure Sentiment Validation for CryptoPulse Bot
Validates and sanitizes LLM responses to prevent security issues
"""

import re
import logging
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """Validation result types"""
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    INVALID_SENTIMENT = "invalid_sentiment"
    INVALID_SYMBOLS = "invalid_symbols"
    NO_DATA = "no_data"


@dataclass
class ValidatedSentiment:
    """Validated sentiment analysis result"""
    is_valid: bool
    symbols: List[str]
    sentiment: Optional[float]
    confidence: float
    validation_result: ValidationResult
    error_message: str = ""
    raw_response: str = ""


class SentimentValidator:
    """
    Secure validator for LLM sentiment analysis responses
    Prevents injection attacks and validates data integrity
    """
    
    # Regex patterns for validation
    VALID_SYMBOL_PATTERN = re.compile(r'^[A-Z]{2,10}(USDT|USDC|BUSD)?$')
    SENTIMENT_PATTERN = re.compile(r'Sentiment:\s*([-+]?\d+(?:\.\d+)?)%')
    COINS_PATTERN = re.compile(r'Coins:\s*([\w, /\-N/A]+)')
    EXPLANATION_PATTERN = re.compile(r'Explanation:\s*(.+)', re.DOTALL)
    
    # Security patterns to detect potential attacks
    SUSPICIOUS_PATTERNS = [
        re.compile(r'<script.*?>', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'data:.*?base64', re.IGNORECASE),
        re.compile(r'eval\s*\(', re.IGNORECASE),
        re.compile(r'exec\s*\(', re.IGNORECASE),
        re.compile(r'import\s+', re.IGNORECASE),
        re.compile(r'__.*__', re.IGNORECASE),  # Python dunder methods
        re.compile(r'SELECT\s+.*\s+FROM', re.IGNORECASE),  # SQL injection
        re.compile(r'DROP\s+TABLE', re.IGNORECASE),
        re.compile(r'DELETE\s+FROM', re.IGNORECASE),
    ]
    
    # Known cryptocurrency symbols (expandable)
    KNOWN_SYMBOLS = {
        'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'AVAX', 'SHIB',
        'MATIC', 'UNI', 'LINK', 'ATOM', 'LTC', 'BCH', 'FTT', 'NEAR', 'ALGO', 'MANA',
        'SAND', 'CRO', 'APE', 'FLOW', 'ICP', 'VET', 'HBAR', 'FIL', 'EGLD', 'XTZ',
        'THETA', 'AXS', 'EOS', 'AAVE', 'BSV', 'GRT', 'KCS', 'RUNE', 'XLM', 'KLAY'
    }
    
    def __init__(self, max_symbols=10, min_confidence=0.7):
        self.max_symbols = max_symbols
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'security_violations': 0,
            'format_errors': 0
        }
    
    def validate_response(self, llm_response: str, 
                         require_explanation: bool = True) -> ValidatedSentiment:
        """
        Main validation method - validates and sanitizes LLM response
        
        Args:
            llm_response: Raw response from LLM
            require_explanation: Whether explanation is required for validation
            
        Returns:
            ValidatedSentiment object with validation results
        """
        self.validation_stats['total_validations'] += 1
        
        # Input sanitization
        if not llm_response or not isinstance(llm_response, str):
            return ValidatedSentiment(
                is_valid=False,
                symbols=[],
                sentiment=None,
                confidence=0.0,
                validation_result=ValidationResult.NO_DATA,
                error_message="Empty or invalid response",
                raw_response=str(llm_response)[:500]  # Limit raw response length
            )
        
        # Limit response length to prevent DoS
        if len(llm_response) > 10000:  # 10KB limit
            self.logger.warning("LLM response too long, truncating")
            llm_response = llm_response[:10000]
        
        # Security validation - check for suspicious patterns
        security_check = self._check_security_violations(llm_response)
        if security_check:
            self.validation_stats['security_violations'] += 1
            return ValidatedSentiment(
                is_valid=False,
                symbols=[],
                sentiment=None,
                confidence=0.0,
                validation_result=ValidationResult.INVALID_FORMAT,
                error_message=f"Security violation detected: {security_check}",
                raw_response=llm_response[:200]
            )
        
        # Extract and validate sentiment
        sentiment, sentiment_confidence = self._extract_and_validate_sentiment(llm_response)
        
        # Extract and validate symbols
        symbols, symbol_confidence = self._extract_and_validate_symbols(llm_response)
        
        # Extract explanation if required
        explanation_confidence = 1.0
        if require_explanation:
            explanation_confidence = self._validate_explanation(llm_response)
        
        # Calculate overall confidence
        overall_confidence = (sentiment_confidence + symbol_confidence + explanation_confidence) / 3
        
        # Determine validation result
        is_valid = (
            sentiment is not None and 
            symbols is not None and 
            overall_confidence >= self.min_confidence
        )
        
        if is_valid:
            self.validation_stats['successful_validations'] += 1
            validation_result = ValidationResult.VALID
            error_message = ""
        else:
            validation_result = self._determine_error_type(sentiment, symbols, overall_confidence)
            error_message = self._generate_error_message(validation_result, overall_confidence)
            self.validation_stats['format_errors'] += 1
        
        return ValidatedSentiment(
            is_valid=is_valid,
            symbols=symbols or [],
            sentiment=sentiment,
            confidence=overall_confidence,
            validation_result=validation_result,
            error_message=error_message,
            raw_response=llm_response[:500]
        )
    
    def _check_security_violations(self, response: str) -> Optional[str]:
        """Check for security violations in the response"""
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.search(response):
                return f"Suspicious pattern detected: {pattern.pattern}"
        return None
    
    def _extract_and_validate_sentiment(self, response: str) -> Tuple[Optional[float], float]:
        """Extract and validate sentiment from response"""
        try:
            match = self.SENTIMENT_PATTERN.search(response)
            if not match:
                return None, 0.0
            
            sentiment_value = float(match.group(1))
            
            # Validate sentiment range
            if not (-100 <= sentiment_value <= 100):
                self.logger.warning(f"Sentiment out of range: {sentiment_value}")
                return None, 0.0
            
            # Calculate confidence based on reasonable sentiment values
            # Very extreme values (close to ±100) get lower confidence
            abs_sentiment = abs(sentiment_value)
            if abs_sentiment > 95:
                confidence = 0.5  # Very extreme, suspicious
            elif abs_sentiment > 80:
                confidence = 0.7  # Extreme but possible
            elif abs_sentiment < 5:
                confidence = 0.6  # Very low sentiment, might be noise
            else:
                confidence = 1.0  # Normal range
            
            return sentiment_value, confidence
            
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error extracting sentiment: {e}")
            return None, 0.0
    
    def _extract_and_validate_symbols(self, response: str) -> Tuple[Optional[List[str]], float]:
        """Extract and validate cryptocurrency symbols from response"""
        try:
            match = self.COINS_PATTERN.search(response)
            if not match:
                return None, 0.0
            
            raw_symbols_text = match.group(1).strip()
            
            # Handle N/A case
            if raw_symbols_text.upper() in ['N/A', 'NONE', 'NULL', '']:
                return [], 1.0  # Valid "no symbols" response
            
            # Split and clean symbols
            raw_symbols = [s.strip().upper() for s in raw_symbols_text.split(',')]
            
            # Filter out empty strings and clean symbols
            raw_symbols = [s for s in raw_symbols if s and s != 'N/A']
            
            if len(raw_symbols) > self.max_symbols:
                self.logger.warning(f"Too many symbols ({len(raw_symbols)}), truncating")
                raw_symbols = raw_symbols[:self.max_symbols]
            
            valid_symbols = []
            confidence_scores = []
            
            for symbol in raw_symbols:
                # Normalize symbol
                normalized = self._normalize_symbol(symbol)
                if not normalized:
                    continue
                
                # Validate symbol format
                if not self.VALID_SYMBOL_PATTERN.match(normalized):
                    self.logger.warning(f"Invalid symbol format: {symbol}")
                    confidence_scores.append(0.0)
                    continue
                
                # Check if it's a known symbol (higher confidence)
                base_symbol = normalized.replace('USDT', '').replace('USDC', '').replace('BUSD', '')
                if base_symbol in self.KNOWN_SYMBOLS:
                    confidence_scores.append(1.0)
                else:
                    confidence_scores.append(0.7)  # Unknown but valid format
                
                valid_symbols.append(normalized)
            
            # Calculate overall symbol confidence
            if not confidence_scores:
                symbol_confidence = 0.0
            else:
                symbol_confidence = sum(confidence_scores) / len(confidence_scores)
            
            return valid_symbols, symbol_confidence
            
        except Exception as e:
            self.logger.error(f"Error extracting symbols: {e}")
            return None, 0.0
    
    def _normalize_symbol(self, symbol: str) -> Optional[str]:
        """Normalize cryptocurrency symbol"""
        if not symbol or len(symbol) < 2:
            return None
        
        # Remove common prefixes/suffixes that might be added by LLM
        symbol = symbol.replace('$', '').replace('#', '').strip()
        
        # Handle common variations
        symbol_map = {
            'BITCOIN': 'BTC',
            'ETHEREUM': 'ETH',
            'BINANCE': 'BNB',
            'RIPPLE': 'XRP',
            'CARDANO': 'ADA',
            'SOLANA': 'SOL',
            'DOGECOIN': 'DOGE',
            'POLYGON': 'MATIC',
        }
        
        symbol_upper = symbol.upper()
        if symbol_upper in symbol_map:
            symbol = symbol_map[symbol_upper]
        else:
            symbol = symbol_upper
        
        # Add USDT if not present and not already a stablecoin
        if not symbol.endswith(('USDT', 'USDC', 'BUSD')):
            symbol += 'USDT'
        
        return symbol
    
    def _validate_explanation(self, response: str) -> float:
        """Validate explanation quality"""
        match = self.EXPLANATION_PATTERN.search(response)
        if not match:
            return 0.0
        
        explanation = match.group(1).strip()
        
        # Basic quality checks
        if len(explanation) < 20:
            return 0.3  # Too short
        elif len(explanation) > 1000:
            return 0.7  # Very long, might be verbose
        else:
            return 1.0  # Reasonable length
    
    def _determine_error_type(self, sentiment: Optional[float], 
                            symbols: Optional[List[str]], 
                            confidence: float) -> ValidationResult:
        """Determine the type of validation error"""
        if sentiment is None and (symbols is None or not symbols):
            return ValidationResult.NO_DATA
        elif sentiment is None:
            return ValidationResult.INVALID_SENTIMENT
        elif symbols is None:
            return ValidationResult.INVALID_SYMBOLS
        elif confidence < self.min_confidence:
            return ValidationResult.INVALID_FORMAT
        else:
            return ValidationResult.VALID
    
    def _generate_error_message(self, validation_result: ValidationResult, 
                              confidence: float) -> str:
        """Generate human-readable error message"""
        messages = {
            ValidationResult.NO_DATA: "No valid sentiment or symbols found in response",
            ValidationResult.INVALID_SENTIMENT: "Invalid or missing sentiment value",
            ValidationResult.INVALID_SYMBOLS: "Invalid or missing cryptocurrency symbols",
            ValidationResult.INVALID_FORMAT: f"Response format invalid (confidence: {confidence:.2f})",
        }
        return messages.get(validation_result, "Unknown validation error")
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        stats = self.validation_stats.copy()
        if stats['total_validations'] > 0:
            stats['success_rate'] = float(stats['successful_validations']) / float(stats['total_validations'])
        else:
            stats['success_rate'] = 0.0
        return stats
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'security_violations': 0,
            'format_errors': 0
        }


# Example usage and testing
def test_validator():
    """Test function for the sentiment validator"""
    validator = SentimentValidator()
    
    # Test cases
    test_responses = [
        # Valid response
        """
        Coins: BTC, ETH, SOL
        Sentiment: 75%
        
        Explanation: The market shows strong bullish sentiment due to institutional adoption.
        """,
        
        # Invalid sentiment
        """
        Coins: BTC, ETH
        Sentiment: 150%
        
        Explanation: Invalid sentiment value test.
        """,
        
        # Security violation attempt
        """
        Coins: BTC<script>alert('xss')</script>
        Sentiment: 50%
        
        Explanation: Attempted XSS injection.
        """,
        
        # No data
        """
        Random text without proper format.
        """,
        
        # Edge case - N/A coins
        """
        Coins: N/A
        Sentiment: 0%
        
        Explanation: No specific coins mentioned in the news.
        """
    ]
    
    print("=== Sentiment Validator Test Results ===\n")
    
    for i, response in enumerate(test_responses, 1):
        print(f"Test {i}:")
        result = validator.validate_response(response.strip())
        
        print(f"  Valid: {result.is_valid}")
        print(f"  Symbols: {result.symbols}")
        print(f"  Sentiment: {result.sentiment}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Result: {result.validation_result.value}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        print()
    
    # Print statistics
    stats = validator.get_validation_stats()
    print("=== Validation Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_validator()