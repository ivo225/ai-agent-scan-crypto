import asyncio
from app.utils.confidence import calculate_confidence_score

def test_twitter_sentiment_impact():
    """
    Test how Twitter sentiment affects confidence scores with our new implementation.
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
    
    # Test 1: No Twitter sentiment
    print("\nTest 1: No Twitter Sentiment")
    result1 = calculate_confidence_score(tech_indicators, current_price)
    print(f"Direction: {result1['direction']}")
    print(f"Signal: {result1['signal']}")
    print(f"Confidence: {result1['overall_score']}")
    
    # Test 2: Bullish with supporting Twitter sentiment
    print("\nTest 2: Bullish with Supporting Twitter Sentiment")
    bullish_twitter = {
        'overall_sentiment': 'bullish',
        'summary': 'Twitter sentiment is generally bullish with positive discussions about price action.',
        'key_tweets': [
            'Tweet 1: "Bitcoin looking strong today! #BTC"',
            'Tweet 2: "Accumulating more $BTC at these levels"',
            'Tweet 3: "Technical breakout imminent for Bitcoin"'
        ]
    }
    result2 = calculate_confidence_score(tech_indicators, current_price, twitter_sentiment=bullish_twitter)
    print(f"Direction: {result2['direction']}")
    print(f"Signal: {result2['signal']}")
    print(f"Confidence: {result2['overall_score']}")
    print("\nSupporting Indicators:")
    for indicator in result2['supporting_indicators']:
        if "Twitter:" in indicator:
            print(f"- {indicator}")
    
    # Test 3: Bullish with conflicting Twitter sentiment
    print("\nTest 3: Bullish with Conflicting Twitter Sentiment")
    bearish_twitter = {
        'overall_sentiment': 'bearish',
        'summary': 'Twitter sentiment is generally bearish with concerns about market conditions.',
        'key_tweets': [
            'Tweet 1: "Bitcoin looking weak, expecting further downside #BTC"',
            'Tweet 2: "Sold my $BTC position, waiting for lower prices"',
            'Tweet 3: "Bear market not over yet for crypto"'
        ]
    }
    result3 = calculate_confidence_score(tech_indicators, current_price, twitter_sentiment=bearish_twitter)
    print(f"Direction: {result3['direction']}")
    print(f"Signal: {result3['signal']}")
    print(f"Confidence: {result3['overall_score']}")
    print("\nConflicting Indicators:")
    for indicator in result3['conflicting_indicators']:
        if "Twitter:" in indicator:
            print(f"- {indicator}")
    
    # Test 4: Combined with market context
    print("\nTest 4: Combined Twitter Sentiment and Market Context")
    market_context = {
        'fear_greed': {'value': '25', 'value_classification': 'Extreme Fear'},
        'global_market': {
            'market_cap_change_percentage_24h_usd': 3.5,
            'market_cap_percentage': {'btc': 45}
        }
    }
    result4 = calculate_confidence_score(
        tech_indicators, 
        current_price, 
        market_context=market_context,
        twitter_sentiment=bullish_twitter
    )
    print(f"Direction: {result4['direction']}")
    print(f"Signal: {result4['signal']}")
    print(f"Confidence: {result4['overall_score']}")
    print("\nFactor Scores:")
    for factor, score in result4['factor_scores'].items():
        print(f"{factor}: {score}")
    
    # Test 5: Neutral Twitter sentiment
    print("\nTest 5: Neutral Twitter Sentiment")
    neutral_twitter = {
        'overall_sentiment': 'neutral',
        'summary': 'Twitter sentiment is mixed with no clear direction.',
        'key_tweets': [
            'Tweet 1: "Bitcoin consolidating in this range"',
            'Tweet 2: "Waiting for clearer signals on $BTC"'
        ]
    }
    result5 = calculate_confidence_score(tech_indicators, current_price, twitter_sentiment=neutral_twitter)
    print(f"Direction: {result5['direction']}")
    print(f"Signal: {result5['signal']}")
    print(f"Confidence: {result5['overall_score']}")

if __name__ == "__main__":
    test_twitter_sentiment_impact()
