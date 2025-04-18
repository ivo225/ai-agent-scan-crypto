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
        # First try using pandas_ta
        try:
            rsi_series = df.ta.rsi()
            # Get the last non-NaN value
            last_rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else None
            results["rsi"] = float(last_rsi) if last_rsi is not None else None
        except Exception as e:
            print(f"pandas_ta RSI calculation failed, trying manual calculation: {e}")

            # Fallback to manual RSI calculation if pandas_ta fails
            if 'close' in df.columns:
                # Ensure close column is numeric
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                # Drop any NaN values
                df_clean = df.dropna(subset=['close'])

                # Calculate price changes
                delta = df_clean['close'].diff()

                # Get gains and losses
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)

                # Calculate average gain and loss over 14 periods (standard RSI)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()

                # Calculate RS and RSI
                rs = avg_gain / avg_loss
                rsi_manual = 100 - (100 / (1 + rs))

                # Get the last value
                last_rsi_manual = rsi_manual.dropna().iloc[-1] if not rsi_manual.dropna().empty else None

                # Explicitly convert to float with error handling
                try:
                    results["rsi"] = float(last_rsi_manual) if last_rsi_manual is not None else None
                    print("Successfully calculated RSI using manual method")
                except (ValueError, TypeError) as e:
                    print(f"Error converting manual RSI to float: {e}")
                    results["rsi"] = None
            else:
                print("Cannot calculate RSI: 'close' column not found")
                results["rsi"] = None
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        results["rsi"] = None

    # MACD (Moving Average Convergence Divergence) - Shorter Period
    try:
        # First try using pandas_ta
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
            else:
                raise Exception("pandas_ta MACD returned None or empty DataFrame")
        except Exception as e:
            print(f"pandas_ta MACD calculation failed, trying manual calculation: {e}")

            # Fallback to manual MACD calculation if pandas_ta fails
            if 'close' in df.columns:
                # Ensure close column is numeric
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                # Drop any NaN values
                df_clean = df.dropna(subset=['close'])

                # Calculate EMAs for MACD
                ema_fast = df_clean['close'].ewm(span=macd_fast, adjust=False).mean()
                ema_slow = df_clean['close'].ewm(span=macd_slow, adjust=False).mean()

                # Calculate MACD line
                macd_line = ema_fast - ema_slow

                # Calculate signal line
                signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()

                # Calculate histogram
                histogram = macd_line - signal_line

                # Get the last values
                last_macd_manual = macd_line.iloc[-1] if not macd_line.empty else None
                last_signal_manual = signal_line.iloc[-1] if not signal_line.empty else None
                last_hist_manual = histogram.iloc[-1] if not histogram.empty else None

                # Explicitly convert to float with error handling
                try:
                    results["macd"] = float(last_macd_manual) if last_macd_manual is not None else None
                    results["macd_signal"] = float(last_signal_manual) if last_signal_manual is not None else None
                    results["macd_hist"] = float(last_hist_manual) if last_hist_manual is not None else None
                    print("Successfully calculated MACD using manual method")
                except (ValueError, TypeError) as e:
                    print(f"Error converting manual MACD to float: {e}")
                    results["macd"] = None
                    results["macd_signal"] = None
                    results["macd_hist"] = None
            else:
                print("Cannot calculate MACD: 'close' column not found")
                results["macd"] = None
                results["macd_signal"] = None
                results["macd_hist"] = None
    except Exception as e:
        print(f"Error calculating MACD ({macd_fast},{macd_slow},{macd_signal}): {e}")
        results["macd"] = None
        results["macd_signal"] = None
        results["macd_hist"] = None

    # Simple Moving Averages (SMA)
    for period in sma_periods:
        try:
            # First try using pandas_ta
            try:
                sma_series = df.ta.sma(length=period)
                if sma_series is not None and not sma_series.empty:
                    last_sma = sma_series.dropna().iloc[-1]
                    results[f"sma_{period}"] = float(last_sma) if last_sma is not None else None
                    continue  # Skip to next period if successful
            except Exception as e:
                print(f"pandas_ta SMA {period} calculation failed, trying pandas directly: {e}")

            # Fallback to pandas rolling if pandas_ta fails
            if 'close' in df.columns:
                # Ensure close column is numeric
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                # Drop any NaN values
                df_clean = df.dropna(subset=['close'])
                # Calculate SMA using pandas
                sma_pd = df_clean['close'].rolling(window=period).mean()
                if not sma_pd.empty:
                    last_sma_pd = sma_pd.dropna().iloc[-1] if not sma_pd.dropna().empty else None
                    # Explicitly convert to float with error handling
                    try:
                        results[f"sma_{period}"] = float(last_sma_pd) if last_sma_pd is not None else None
                        print(f"Successfully calculated SMA {period} using pandas rolling")
                    except (ValueError, TypeError) as e:
                        print(f"Error converting SMA {period} to float: {e}, value: {last_sma_pd}, type: {type(last_sma_pd)}")
                        results[f"sma_{period}"] = None
                else:
                    print(f"SMA {period} calculation resulted in empty series")
                    results[f"sma_{period}"] = None
            else:
                print(f"Cannot calculate SMA {period}: 'close' column not found")
                results[f"sma_{period}"] = None
        except Exception as e:
            print(f"Error calculating SMA {period}: {e}")
            results[f"sma_{period}"] = None

    # Exponential Moving Averages (EMA)
    for period in ema_periods:
        try:
            # First try using pandas_ta
            try:
                ema_series = df.ta.ema(length=period)
                if ema_series is not None and not ema_series.empty:
                    last_ema = ema_series.dropna().iloc[-1]
                    results[f"ema_{period}"] = float(last_ema) if last_ema is not None else None
                    continue  # Skip to next period if successful
            except Exception as e:
                print(f"pandas_ta EMA {period} calculation failed, trying pandas directly: {e}")

            # Fallback to pandas ewm if pandas_ta fails
            if 'close' in df.columns:
                # Ensure close column is numeric
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                # Drop any NaN values
                df_clean = df.dropna(subset=['close'])
                # Calculate EMA using pandas
                ema_pd = df_clean['close'].ewm(span=period, adjust=False).mean()
                if not ema_pd.empty:
                    last_ema_pd = ema_pd.iloc[-1]
                    # Explicitly convert to float with error handling
                    try:
                        results[f"ema_{period}"] = float(last_ema_pd)
                        print(f"Successfully calculated EMA {period} using pandas ewm")
                    except (ValueError, TypeError) as e:
                        print(f"Error converting EMA {period} to float: {e}, value: {last_ema_pd}, type: {type(last_ema_pd)}")
                        results[f"ema_{period}"] = None
            else:
                print(f"Cannot calculate EMA {period}: 'close' column not found")
                results[f"ema_{period}"] = None
        except Exception as e:
            print(f"Error calculating EMA {period}: {e}")
            results[f"ema_{period}"] = None

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
