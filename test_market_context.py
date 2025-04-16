from app.utils.confidence import calculate_confidence_score

def test_market_context_impact():
    """
    Test how market context affects confidence scores with our new implementation.
    """
    # Basic technical indicators (simplified for testing)
    tech_indicators = {
        'rsi': 55,  # Neutral
        'macd': 0.5,
        'macd_signal': 0.2,
        'macd_hist': 0.3,
        'bb_upper': 110,
        'bb_middle': 100,
        'bb_lower': 90,
        'sma_50': 98,
        'adx': 25,
        'adx_plus_di': 20,
        'adx_minus_di': 15,
        'ema_9': 102,
        'ema_21': 101,
        'ema_55': 100
    }
    
    current_price = 105  # Slightly bullish
    
    # Test 1: No market context
    print("\nTest 1: No Market Context")
    result1 = calculate_confidence_score(tech_indicators, current_price)
    print(f"Direction: {result1['direction']}")
    print(f"Signal: {result1['signal']}")
    print(f"Confidence: {result1['overall_score']}")
    
    # Test 2: Bullish with supporting market context
    print("\nTest 2: Bullish with Supporting Market Context")
    bullish_market = {
        'fear_greed': {'value': '25', 'value_classification': 'Extreme Fear'},
        'global_market': {
            'market_cap_change_percentage_24h_usd': 3.5,
            'market_cap_percentage': {'btc': 45}
        }
    }
    result2 = calculate_confidence_score(tech_indicators, current_price, bullish_market)
    print(f"Direction: {result2['direction']}")
    print(f"Signal: {result2['signal']}")
    print(f"Confidence: {result2['overall_score']}")
    print("\nSupporting Indicators:")
    for indicator in result2['supporting_indicators']:
        if "Context:" in indicator:
            print(f"- {indicator}")
    
    # Test 3: Bullish with conflicting market context
    print("\nTest 3: Bullish with Conflicting Market Context")
    bearish_market = {
        'fear_greed': {'value': '80', 'value_classification': 'Extreme Greed'},
        'global_market': {
            'market_cap_change_percentage_24h_usd': -6.0,
            'market_cap_percentage': {'btc': 55}
        }
    }
    result3 = calculate_confidence_score(tech_indicators, current_price, bearish_market)
    print(f"Direction: {result3['direction']}")
    print(f"Signal: {result3['signal']}")
    print(f"Confidence: {result3['overall_score']}")
    print("\nConflicting Indicators:")
    for indicator in result3['conflicting_indicators']:
        if "Context:" in indicator:
            print(f"- {indicator}")
    
    # Test 4: Bearish with supporting market context
    print("\nTest 4: Bearish with Supporting Market Context")
    # Modify indicators to be bearish
    bearish_indicators = tech_indicators.copy()
    bearish_indicators['rsi'] = 75
    bearish_indicators['macd'] = -0.5
    bearish_indicators['macd_signal'] = 0.2
    bearish_indicators['macd_hist'] = -0.7
    bearish_indicators['ema_9'] = 98
    bearish_indicators['ema_21'] = 99
    bearish_indicators['ema_55'] = 100
    bearish_price = 95
    
    bearish_supporting_market = {
        'fear_greed': {'value': '80', 'value_classification': 'Extreme Greed'},
        'global_market': {
            'market_cap_change_percentage_24h_usd': -6.0,
            'market_cap_percentage': {'btc': 55}
        }
    }
    result4 = calculate_confidence_score(bearish_indicators, bearish_price, bearish_supporting_market)
    print(f"Direction: {result4['direction']}")
    print(f"Signal: {result4['signal']}")
    print(f"Confidence: {result4['overall_score']}")
    print("\nSupporting Indicators:")
    for indicator in result4['supporting_indicators']:
        if "Context:" in indicator:
            print(f"- {indicator}")

if __name__ == "__main__":
    test_market_context_impact()
