import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional, List # Import List

# Define default periods for various indicators
def calculate_technical_indicators(df: pd.DataFrame,
                               sma_periods: List[int] = [50],
                               ema_periods: List[int] = [9, 21, 55],
                               bbands_length: int = 20,
                               bbands_std: int = 2,
                               macd_fast: int = 8,
                               macd_slow: int = 17,
                               macd_signal: int = 9,
                               adx_length: int = 14) -> Dict[str, Optional[float]]:
    """
    Calculates technical indicators (RSI, MACD, SMA, EMA, ADX, Bollinger Bands) using pandas-ta.

    Args:
        df: A pandas DataFrame with 'open', 'high', 'low', 'close' columns,
            indexed by datetime.
        sma_periods: List of periods for Simple Moving Average calculation.
        ema_periods: List of periods for Exponential Moving Average calculation.
        bbands_length: Period for Bollinger Bands calculation.
        bbands_std: Standard deviation multiplier for Bollinger Bands.
        macd_fast: Fast period for MACD calculation.
        macd_slow: Slow period for MACD calculation.
        macd_signal: Signal period for MACD calculation.
        adx_length: Period for ADX calculation.

    Returns:
        A dictionary containing the latest calculated indicator values.
        Returns None for an indicator if calculation fails or data is insufficient.
    """
    # Initialize results dictionary with all expected keys
    results = {
        "rsi": None, "macd": None, "macd_signal": None, "macd_hist": None,
        "bb_upper": None, "bb_middle": None, "bb_lower": None,
        "sma_50": None,  # Always include sma_50 regardless of sma_periods
        "adx": None, "adx_plus_di": None, "adx_minus_di": None  # ADX and directional indicators
    }
    # Add SMA periods
    for period in sma_periods:
        results[f"sma_{period}"] = None

    # Add EMA periods
    for period in ema_periods:
        results[f"ema_{period}"] = None

    if df is None or df.empty:
        print("Warning: DataFrame is empty, cannot calculate indicators.")
        return results # Return initialized dict

    # Ensure required columns exist (case-insensitive check)
    required_columns = ['open', 'high', 'low', 'close']
    # Ensure 'close' column exists for most indicators
    df.columns = df.columns.str.lower() # Normalize column names
    if 'close' not in df.columns:
         print(f"Warning: DataFrame missing 'close' column, essential for most indicators.")
         return results # Return initialized dict
    if not all(col in df.columns for col in required_columns):
        print(f"Warning: DataFrame missing one or more required columns for some indicators: {required_columns}")
        # Proceed with calculations that are possible

    # --- Calculate Indicators ---

    # RSI (Relative Strength Index)
    try:
        rsi_series = df.ta.rsi()
        # Get the last non-NaN value
        last_rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else None
        results["rsi"] = float(last_rsi) if last_rsi is not None else None
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        # results["rsi"] remains None

    # MACD (Moving Average Convergence Divergence) - Shorter Period
    try:
        macd_df = df.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal)
        if macd_df is not None and not macd_df.empty:
            # Column names depend on the parameters used
            macd_col = f'MACD_{macd_fast}_{macd_slow}_{macd_signal}'
            signal_col = f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}'
            hist_col = f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}'

            last_macd = macd_df[macd_col].dropna().iloc[-1] if not macd_df[macd_col].dropna().empty else None
            last_signal = macd_df[signal_col].dropna().iloc[-1] if not macd_df[signal_col].dropna().empty else None
            last_hist = macd_df[hist_col].dropna().iloc[-1] if not macd_df[hist_col].dropna().empty else None

            results["macd"] = float(last_macd) if last_macd is not None else None
            results["macd_signal"] = float(last_signal) if last_signal is not None else None
            results["macd_hist"] = float(last_hist) if last_hist is not None else None
        # else: results remain None
    except KeyError as e:
         print(f"KeyError calculating MACD (likely column name mismatch or insufficient data): {e}")
         # results remain None
    except Exception as e:
        print(f"Error calculating MACD ({macd_fast},{macd_slow},{macd_signal}): {e}")
        # results remain None

    # Simple Moving Averages (SMA)
    for period in sma_periods:
        try:
            sma_series = df.ta.sma(length=period)
            if sma_series is not None and not sma_series.empty:
                last_sma = sma_series.dropna().iloc[-1]
                results[f"sma_{period}"] = float(last_sma) if last_sma is not None else None
            # else: result remains None
        except Exception as e:
            print(f"Error calculating SMA {period}: {e}")
            # result remains None

    # Exponential Moving Averages (EMA)
    for period in ema_periods:
        try:
            ema_series = df.ta.ema(length=period)
            if ema_series is not None and not ema_series.empty:
                last_ema = ema_series.dropna().iloc[-1]
                results[f"ema_{period}"] = float(last_ema) if last_ema is not None else None
            # else: result remains None
        except Exception as e:
            print(f"Error calculating EMA {period}: {e}")
            # result remains None

    # Average Directional Index (ADX)
    try:
        adx_df = df.ta.adx(length=adx_length)
        if adx_df is not None and not adx_df.empty:
            # Column names for ADX indicators
            adx_col = f'ADX_{adx_length}'
            plus_di_col = f'DMP_{adx_length}'
            minus_di_col = f'DMN_{adx_length}'

            last_adx = adx_df[adx_col].dropna().iloc[-1] if not adx_df[adx_col].dropna().empty else None
            last_plus_di = adx_df[plus_di_col].dropna().iloc[-1] if not adx_df[plus_di_col].dropna().empty else None
            last_minus_di = adx_df[minus_di_col].dropna().iloc[-1] if not adx_df[minus_di_col].dropna().empty else None

            results["adx"] = float(last_adx) if last_adx is not None else None
            results["adx_plus_di"] = float(last_plus_di) if last_plus_di is not None else None
            results["adx_minus_di"] = float(last_minus_di) if last_minus_di is not None else None
        # else: results remain None
    except KeyError as e:
        print(f"KeyError calculating ADX (likely column name mismatch or insufficient data): {e}")
        # results remain None
    except Exception as e:
        print(f"Error calculating ADX (length={adx_length}): {e}")
        # results remain None

    # Bollinger Bands (BBands)
    try:
        bbands_df = df.ta.bbands(length=bbands_length, std=bbands_std)
        if bbands_df is not None and not bbands_df.empty:
            # Column names depend on parameters
            upper_col = f'BBU_{bbands_length}_{bbands_std}.0'
            middle_col = f'BBM_{bbands_length}_{bbands_std}.0'
            lower_col = f'BBL_{bbands_length}_{bbands_std}.0'

            last_upper = bbands_df[upper_col].dropna().iloc[-1] if not bbands_df[upper_col].dropna().empty else None
            last_middle = bbands_df[middle_col].dropna().iloc[-1] if not bbands_df[middle_col].dropna().empty else None
            last_lower = bbands_df[lower_col].dropna().iloc[-1] if not bbands_df[lower_col].dropna().empty else None

            results["bb_upper"] = float(last_upper) if last_upper is not None else None
            results["bb_middle"] = float(last_middle) if last_middle is not None else None
            results["bb_lower"] = float(last_lower) if last_lower is not None else None
        # else: results remain None
    except KeyError as e:
        print(f"KeyError calculating Bollinger Bands (likely column name mismatch or insufficient data): {e}")
        # results remain None
    except Exception as e:
        print(f"Error calculating Bollinger Bands ({bbands_length},{bbands_std}): {e}")
        # results remain None

    return results

# Example usage (can be removed or moved to tests)
# import asyncio
# from app.services.coin_gecko_service import get_historical_ohlc
#
# async def main():
#     ohlc_df = await get_historical_ohlc("bitcoin", days=100) # Need enough data for indicators
#     if ohlc_df is not None:
#         indicators = calculate_technical_indicators(ohlc_df)
#         print("\n--- Calculated Technical Indicators ---")
#         print(indicators)
#
# if __name__ == "__main__":
#     asyncio.run(main())
