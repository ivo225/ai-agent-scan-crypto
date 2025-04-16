from typing import Dict, Optional, Any # Import Any

# Use the new function for fetching data
from app.services.coin_gecko_service import get_historical_market_data
from app.utils.indicators import calculate_technical_indicators
from app.utils.confidence import calculate_confidence_score # Import confidence calculator
from app.services.market_context_service import get_market_context # Import market context service

# Increase default days for better long-term indicator calculation (e.g., SMA 200)
async def get_technical_analysis(coin_id: str, vs_currency: str = "usd", days: int = 365) -> Optional[Dict[str, Any]]: # Return type includes confidence dict
    """
    Performs technical analysis by fetching historical market data, calculating indicators,
    and determining a prediction confidence score.

    Args:
        coin_id: The CoinGecko identifier for the coin.
        vs_currency: The target currency (default: 'usd').
        days: Number of days of historical data to fetch for analysis (default: 365).

    Returns:
        A dictionary containing the latest calculated indicator values and a 'confidence' sub-dictionary,
        or None if historical data couldn't be fetched.
    """
    print(f"Performing technical analysis and confidence scoring for {coin_id}/{vs_currency} using up to {days} days of data...")

    # 1. Fetch historical market data using the new function
    ohlcv_df = await get_historical_market_data(coin_id=coin_id, vs_currency=vs_currency, days=days)

    if ohlcv_df is None or ohlcv_df.empty:
        print(f"Could not fetch or process historical market data for {coin_id}. Skipping technical analysis.")
        return None # Indicate failure to get data

    # 2. Calculate indicators using the processed OHLCV data
    print(f"Calculating indicators using data from {ohlcv_df.index.min()} to {ohlcv_df.index.max()}...")
    try:
        indicators = calculate_technical_indicators(ohlcv_df)
    except Exception as e:
        print(f"Error calculating indicators for {coin_id}: {e}")
        return None # Indicate failure during calculation

    # 3. Fetch Market Context (Do this before confidence calculation)
    market_context = await get_market_context()

    # 4. Calculate Confidence Score
    current_price = ohlcv_df['close'].iloc[-1] if not ohlcv_df.empty else None
    if current_price is None:
         print(f"Warning: Could not determine current price for {coin_id}. Confidence score might be affected.")

    try:
        # Pass market_context to the confidence calculation
        confidence_data = calculate_confidence_score(
            tech_indicators=indicators,
            price=current_price,
            market_context=market_context # Pass the fetched context
        )
    except Exception as e:
        print(f"Error calculating confidence score for {coin_id}: {e}")
        # Proceed without confidence score or return None? Let's proceed but log error.
        confidence_data = {"error": "Failed to calculate confidence score"}


    # 5. Merge indicators and confidence data
    # Make sure all expected keys are present in the result
    expected_keys = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'sma_50', 'bb_upper', 'bb_middle', 'bb_lower',
                    'adx', 'adx_plus_di', 'adx_minus_di', 'ema_9', 'ema_21', 'ema_55']
    for key in expected_keys:
        if key not in indicators:
            indicators[key] = None

    # Add current price to indicators for reference in display formatting
    if current_price is not None:
        indicators['current_price'] = current_price

    result = {**indicators, 'confidence': confidence_data}

    print(f"Calculated indicators for {coin_id}: {indicators}")
    print(f"Calculated confidence score: {confidence_data.get('overall_score', 'N/A')}, Direction: {confidence_data.get('direction', 'N/A')}")
    return result

# Example usage (can be removed or moved to tests)
# import asyncio
#
# async def main():
#     ta_results = await get_technical_analysis("bitcoin", days=100)
#     if ta_results:
#         print("\n--- Technical Analysis Results ---")
#         print(ta_results)
#     else:
#         print("Technical analysis failed.")
#
# if __name__ == "__main__":
#     asyncio.run(main())
