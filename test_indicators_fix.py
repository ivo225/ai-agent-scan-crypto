import asyncio
from app.services.technical_analysis_service import get_technical_analysis

async def test_indicators():
    """
    Test the technical analysis with our improved indicator calculations.
    """
    print("Testing technical analysis with improved indicator calculations...")
    
    # Test with a few different cryptocurrencies
    coins = ["bitcoin", "ethereum", "ripple", "cardano", "solana"]
    
    for coin in coins:
        print(f"\n{'='*50}\nTesting {coin}\n{'='*50}")
        try:
            # Use fewer days to avoid rate limiting
            ta_results = await get_technical_analysis(coin, days=30)
            
            if ta_results:
                # Check if EMA 55 was calculated successfully
                ema_55 = ta_results.get('ema_55')
                print(f"EMA 55: {ema_55}")
                
                # Check other key indicators
                print(f"RSI: {ta_results.get('rsi')}")
                print(f"MACD: {ta_results.get('macd')}")
                print(f"MACD Signal: {ta_results.get('macd_signal')}")
                print(f"MACD Hist: {ta_results.get('macd_hist')}")
                
                # Check confidence score
                confidence = ta_results.get('confidence', {})
                print(f"Confidence Score: {confidence.get('overall_score')}")
                print(f"Direction: {confidence.get('direction')}")
                print(f"Signal: {confidence.get('signal')}")
            else:
                print(f"Technical analysis failed for {coin}")
        except Exception as e:
            print(f"Error testing {coin}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_indicators())
