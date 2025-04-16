import asyncio
from app.utils.confidence import generate_trading_signal

def test_trading_signals():
    print("Testing trading signal generation with various scenarios...")
    
    # Test case 1: Strong bullish scenario
    print("\nTest Case 1: Strong Bullish Scenario")
    tech_indicators = {
        'rsi': 65,  # Moderately bullish
        'adx': 35,  # Strong trend
        'adx_plus_di': 30,  # Bullish trend (DI+ > DI-)
        'adx_minus_di': 15,
        'macd': 10,  # MACD above signal
        'macd_signal': 5,
        'macd_hist': 5,  # Positive and significant
        'ema_9': 110,  # Perfect bullish alignment
        'ema_21': 105,
        'ema_55': 100,
        'current_price': 115  # Price above all EMAs
    }
    signal = generate_trading_signal(65, 'bullish', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")
    
    # Test case 2: Moderate bullish scenario
    print("\nTest Case 2: Moderate Bullish Scenario")
    tech_indicators = {
        'rsi': 55,  # Neutral
        'adx': 25,  # Moderate trend
        'adx_plus_di': 25,  # Bullish trend (DI+ > DI-)
        'adx_minus_di': 20,
        'macd': 5,  # MACD above signal
        'macd_signal': 3,
        'macd_hist': 2,  # Positive but not significant
        'ema_9': 105,  # Short-term bullish only
        'ema_21': 100,
        'ema_55': 110,  # Not perfect alignment
        'current_price': 107  # Price below long-term EMA
    }
    signal = generate_trading_signal(45, 'bullish', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")
    
    # Test case 3: Neutral scenario
    print("\nTest Case 3: Neutral Scenario")
    tech_indicators = {
        'rsi': 50,  # Neutral
        'adx': 15,  # Weak trend
        'adx_plus_di': 18,  # Slightly bullish
        'adx_minus_di': 16,
        'macd': -2,  # MACD below signal
        'macd_signal': 0,
        'macd_hist': -2,  # Negative but not significant
        'ema_9': 100,  # Mixed signals
        'ema_21': 102,
        'ema_55': 98,
        'current_price': 101  # Price above some EMAs, below others
    }
    signal = generate_trading_signal(35, 'neutral', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")
    
    # Test case 4: Moderate bearish scenario
    print("\nTest Case 4: Moderate Bearish Scenario")
    tech_indicators = {
        'rsi': 35,  # Approaching oversold
        'adx': 28,  # Moderate trend
        'adx_plus_di': 15,  # Bearish trend (DI- > DI+)
        'adx_minus_di': 25,
        'macd': -8,  # MACD below signal
        'macd_signal': -5,
        'macd_hist': -3,  # Negative
        'ema_9': 90,  # Short-term bearish
        'ema_21': 95,
        'ema_55': 100,
        'current_price': 85  # Price below all EMAs
    }
    signal = generate_trading_signal(50, 'bearish', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")
    
    # Test case 5: Strong bearish scenario
    print("\nTest Case 5: Strong Bearish Scenario")
    tech_indicators = {
        'rsi': 25,  # Oversold
        'adx': 40,  # Very strong trend
        'adx_plus_di': 10,  # Strongly bearish trend
        'adx_minus_di': 35,
        'macd': -15,  # MACD far below signal
        'macd_signal': -8,
        'macd_hist': -7,  # Strongly negative
        'ema_9': 80,  # Perfect bearish alignment
        'ema_21': 90,
        'ema_55': 100,
        'current_price': 75  # Price far below all EMAs
    }
    signal = generate_trading_signal(70, 'bearish', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")
    
    # Test case 6: Extreme oversold (potential reversal)
    print("\nTest Case 6: Extreme Oversold (Potential Reversal)")
    tech_indicators = {
        'rsi': 15,  # Extremely oversold
        'adx': 35,  # Strong trend
        'adx_plus_di': 20,  # Starting to turn bullish
        'adx_minus_di': 30,  # Still bearish but weakening
        'macd': -10,  # MACD below signal
        'macd_signal': -5,
        'macd_hist': -5,  # Negative but flattening
        'ema_9': 85,  # Bearish alignment
        'ema_21': 90,
        'ema_55': 100,
        'current_price': 80  # Price below all EMAs
    }
    signal = generate_trading_signal(30, 'bearish', tech_indicators.get('current_price'), tech_indicators)
    print(f"Signal: {signal}")

if __name__ == "__main__":
    test_trading_signals()
