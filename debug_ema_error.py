import asyncio
import pandas as pd
import pandas_ta as ta
from app.services.coin_gecko_service import get_historical_market_data

async def debug_ema_calculation(coin_id: str = "bitcoin", days: int = 365):
    """
    Debug the EMA calculation error by examining the data and calculation process.
    """
    print(f"Debugging EMA calculation for {coin_id} with {days} days of data...")

    # 1. Fetch historical market data
    ohlcv_df = await get_historical_market_data(coin_id=coin_id, vs_currency="usd", days=days)

    if ohlcv_df is None or ohlcv_df.empty:
        print(f"Could not fetch or process historical market data for {coin_id}.")
        return

    # 2. Print data info
    print("\nDataFrame Info:")
    print(f"Shape: {ohlcv_df.shape}")
    print(f"Columns: {ohlcv_df.columns.tolist()}")
    print(f"Data types: {ohlcv_df.dtypes}")
    print(f"Any NaN values: {ohlcv_df.isna().any().any()}")

    # 3. Try calculating EMA with different approaches
    print("\nAttempting EMA calculations with different approaches...")

    # Approach 1: Using pandas_ta directly
    try:
        print("\nApproach 1: Using pandas_ta directly")
        ema_series = ohlcv_df.ta.ema(length=55)
        if ema_series is not None and not ema_series.empty:
            last_ema = ema_series.dropna().iloc[-1]
            print(f"Last EMA 55 value: {last_ema}")
            print(f"Type of last_ema: {type(last_ema)}")
            # Try explicit conversion
            ema_float = float(last_ema)
            print(f"Converted to float: {ema_float}")
        else:
            print("EMA series is None or empty")
    except Exception as e:
        print(f"Error in Approach 1: {e}")

    # Approach 2: Using pandas directly
    try:
        print("\nApproach 2: Using pandas directly")
        ema_pd = ohlcv_df['close'].ewm(span=55, adjust=False).mean()
        last_ema_pd = ema_pd.iloc[-1]
        print(f"Last EMA 55 value (pandas): {last_ema_pd}")
        print(f"Type of last_ema_pd: {type(last_ema_pd)}")
        # Try explicit conversion
        ema_pd_float = float(last_ema_pd)
        print(f"Converted to float: {ema_pd_float}")
    except Exception as e:
        print(f"Error in Approach 2: {e}")

    # Approach 3: Manual calculation with explicit type conversion
    try:
        print("\nApproach 3: Manual calculation with explicit type conversion")
        # Ensure close column is numeric
        ohlcv_df['close'] = pd.to_numeric(ohlcv_df['close'], errors='coerce')
        # Drop any NaN values
        ohlcv_df_clean = ohlcv_df.dropna(subset=['close'])
        # Calculate EMA
        ema_manual = ohlcv_df_clean['close'].ewm(span=55, adjust=False).mean()
        last_ema_manual = ema_manual.iloc[-1]
        print(f"Last EMA 55 value (manual): {last_ema_manual}")
        print(f"Type of last_ema_manual: {type(last_ema_manual)}")
        # Try explicit conversion
        ema_manual_float = float(last_ema_manual)
        print(f"Converted to float: {ema_manual_float}")
    except Exception as e:
        print(f"Error in Approach 3: {e}")

    # 4. Check the last few values of the close column
    print("\nLast 5 values of 'close' column:")
    print(ohlcv_df['close'].tail(5))
    print(f"Types of last 5 values: {[type(x) for x in ohlcv_df['close'].tail(5).values]}")

async def test_multiple_coins():
    """Test EMA calculation with multiple coins to find the problematic one."""
    coins = ["bitcoin", "ethereum", "ripple", "cardano", "solana", "dogecoin", "shiba-inu"]

    for coin in coins:
        print(f"\n{'='*50}\nTesting {coin}\n{'='*50}")
        try:
            await debug_ema_calculation(coin, days=90)  # Use fewer days for faster testing
        except Exception as e:
            print(f"Error with {coin}: {e}")

if __name__ == "__main__":
    asyncio.run(test_multiple_coins())
