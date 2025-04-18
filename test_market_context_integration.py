import asyncio
import json
from app.services.market_context_service import get_market_context
from app.utils.confidence import calculate_confidence_score

async def test_enhanced_market_context():
    """
    Test the enhanced market context integration.
    """
    print("\n=== Testing Enhanced Market Context Integration ===\n")
    
    # 1. Fetch the enhanced market context data
    print("Fetching enhanced market context data...")
    market_context = await get_market_context()
    
    # 2. Print the structure and content of the market context data
    print("\nMarket Context Structure:")
    for key, value in market_context.items():
        if value:
            print(f"\n--- {key} ---")
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    # Limit output length for readability
                    if isinstance(subvalue, (list, dict)):
                        print(f"  {subkey}: {type(subvalue).__name__} with {len(subvalue)} items")
                    else:
                        print(f"  {subkey}: {subvalue}")
    
    # 3. Test the confidence calculation with the enhanced market context
    print("\nTesting confidence calculation with enhanced market context...")
    
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
    
    # Test with real market context
    result = calculate_confidence_score(tech_indicators, current_price, market_context)
    
    print(f"\nConfidence Calculation Results:")
    print(f"Direction: {result['direction']}")
    print(f"Signal: {result['signal']}")
    print(f"Confidence Score: {result['overall_score']}")
    
    print("\nFactor Scores:")
    for factor, score in result['factor_scores'].items():
        print(f"  {factor}: {score}")
    
    print("\nSupporting Indicators:")
    for indicator in result['supporting_indicators']:
        print(f"- {indicator}")
    
    print("\nConflicting Indicators:")
    for indicator in result['conflicting_indicators']:
        print(f"- {indicator}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_market_context())
