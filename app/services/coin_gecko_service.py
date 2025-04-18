import httpx
import pandas as pd
import asyncio
import logging
from typing import Optional, List, Tuple, Dict, Any
from pydantic import ValidationError
from datetime import datetime, timedelta

from app.models.coin import CoinData
from app.utils.cache_manager import cache_manager, cached

COINGECKO_API_BASE_URL = "https://api.coingecko.com/api/v3"

# Setup logging
logger = logging.getLogger(__name__)

async def _fetch_coin_list() -> Optional[List[Dict[str, Any]]]:
    """Fetches the full coin list from CoinGecko."""
    api_url = f"{COINGECKO_API_BASE_URL}/coins/list"
    logger.info("Fetching full coin list from CoinGecko (this might take a moment)...")
    async with httpx.AsyncClient(timeout=30.0) as client: # Increased timeout for potentially large list
        try:
            response = await client.get(api_url)
            response.raise_for_status()
            coin_list = response.json()
            logger.info(f"Successfully fetched {len(coin_list)} coins.")
            return coin_list
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching coin list: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error fetching coin list: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching coin list: {e}")
            return None

async def get_coin_list() -> Optional[List[Dict[str, Any]]]:
    """Gets the coin list from cache or fetches it if not cached."""
    # Try to get from cache first
    cached_list = await cache_manager.get('coingecko_list', 'coins_list')
    if cached_list is not None:
        logger.debug(f"Using cached coin list with {len(cached_list)} coins")
        return cached_list

    # Cache miss, fetch and cache
    coin_list = await _fetch_coin_list()
    if coin_list is not None:
        # Cache for 1 hour (3600 seconds)
        await cache_manager.set('coingecko_list', 'coins_list', coin_list)

    return coin_list

async def get_coin_id_from_symbol(symbol: str) -> Optional[str]:
    """
    Finds the CoinGecko coin ID based on the ticker symbol.

    Args:
        symbol: The coin's ticker symbol (e.g., 'btc', 'eth', 'icp'). Case-insensitive.

    Returns:
        The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'internet-computer') if found,
        otherwise None. Returns the first match found.
    """
    target_symbol = symbol.lower()

    # Get the coin list from cache or fetch it
    coin_list = await get_coin_list()
    if coin_list is None:
        logger.error("Error: Coin list is unavailable.")
        return None

    # --- Improved Symbol Matching Logic ---
    exact_id_match = None
    symbol_matches = []
    name_matches = [] # Also consider matching the name

    for coin in coin_list:
        coin_id = coin.get('id', '').lower()
        coin_symbol = coin.get('symbol', '').lower()
        coin_name = coin.get('name', '').lower()

        # Priority 1: Exact ID match (e.g., user enters 'bitcoin')
        if coin_id == target_symbol:
            exact_id_match = coin
            break # Found the best possible match

        # Priority 2: Exact symbol match
        if coin_symbol == target_symbol:
            symbol_matches.append(coin)

        # Priority 3: Exact name match (case-insensitive)
        elif coin_name == target_symbol:
             name_matches.append(coin)


    if exact_id_match:
        best_match = exact_id_match
        logger.info(f"Found exact ID match for '{symbol}': '{best_match.get('id')}'")
    elif symbol_matches:
        # Among symbol matches, prioritize shorter IDs or common names if possible
        # Simple heuristic: prefer the one where id == symbol (e.g., 'btc' id for 'btc' symbol if it exists)
        # Or prefer common names like 'bitcoin', 'ethereum'
        preferred_match = None
        common_names = {'bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana', 'ripple', 'cardano', 'dogecoin', 'polkadot', 'litecoin', 'chainlink'} # Add more if needed
        for coin in symbol_matches:
            coin_id = coin.get('id', '')
            if coin_id == target_symbol or coin_id in common_names:
                 preferred_match = coin
                 break
        best_match = preferred_match if preferred_match else symbol_matches[0] # Fallback to first symbol match
        logger.info(f"Resolved symbol '{symbol}' to CoinGecko ID '{best_match.get('id')}' (from {len(symbol_matches)} symbol matches).")
    elif name_matches:
         # If only name matches were found, take the first one
         best_match = name_matches[0]
         logger.info(f"Resolved name '{symbol}' to CoinGecko ID '{best_match.get('id')}' (from {len(name_matches)} name matches).")
    else:
        logger.warning(f"Could not find any CoinGecko entries for symbol or name '{symbol}'.")
        return None

    return best_match.get('id')


@cached('coingecko', lambda coin_id, **kwargs: f"coin_data_{coin_id}")
async def get_coin_data_by_id(coin_id: str) -> Optional[CoinData]:
    """
    Fetches detailed coin data from CoinGecko API by coin ID.
    Results are cached to reduce API calls.

    Args:
        coin_id: The CoinGecko identifier for the coin (e.g., 'bitcoin').

    Returns:
        A CoinData object if successful, None otherwise.
        Raises httpx.HTTPStatusError for API errors (4xx, 5xx).
    """
    api_url = f"{COINGECKO_API_BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",        # Keep descriptions in original language
        "tickers": "false",             # Exclude ticker data
        "market_data": "true",          # Include market data
        "community_data": "false",      # Exclude community data
        "developer_data": "false",      # Exclude developer data
        "sparkline": "false"            # Exclude sparkline data
    }

    logger.info(f"Fetching coin data for {coin_id} from CoinGecko")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status()  # Raise exception for 4xx/5xx errors

            data = response.json()
            # Basic check if essential data is present before validation
            if not data or 'id' not in data or 'market_data' not in data:
                 logger.error(f"Error: Incomplete data received for coin ID {coin_id}")
                 return None

            validated_data = CoinData.parse_obj(data) # Use model_validate for Pydantic v2
            return validated_data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching data for {coin_id}: {e.response.status_code} - {e.response.text}")
            # Re-raise or handle specific errors (e.g., 404, 429)
            raise e
        except httpx.RequestError as e:
            logger.error(f"Network error fetching data for {coin_id}: {e}")
            return None # Or raise a custom network error
        except ValidationError as e:
            logger.error(f"Data validation error for {coin_id}: {e}")
            return None # Or raise a custom validation error
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching data for {coin_id}: {e}")
            return None # Or raise a generic error


@cached('coingecko_market', lambda coin_id, vs_currency='usd', days=90, **kwargs: f"ohlc_{coin_id}_{vs_currency}_{days}")
async def get_historical_ohlc(coin_id: str, vs_currency: str = "usd", days: int = 90) -> Optional[pd.DataFrame]:
    """
    Fetches historical OHLC data for a coin from CoinGecko.
    Results are cached to reduce API calls.

    Args:
        coin_id: The CoinGecko identifier for the coin.
        vs_currency: The target currency (default: 'usd').
        days: Number of days of historical data to fetch (default: 90).

    Returns:
        A pandas DataFrame with OHLC data indexed by datetime, or None on error.
        Columns: 'open', 'high', 'low', 'close', 'volume'
    """
    api_url = f"{COINGECKO_API_BASE_URL}/coins/{coin_id}/ohlc"
    params = {
        "vs_currency": vs_currency.lower(),
        "days": str(days),
    }

    logger.info(f"Fetching historical OHLC data for {coin_id}/{vs_currency} ({days} days) from CoinGecko")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status()

            data = response.json()

            if not data:
                logger.warning(f"No historical OHLC data found for {coin_id} / {vs_currency}.")
                return None

            # Convert to DataFrame
            # Data format: [[timestamp_ms, open, high, low, close], ...]
            df = pd.DataFrame(data, columns=['timestamp_ms', 'open', 'high', 'low', 'close'])

            # Convert timestamp (milliseconds) to datetime and set as index
            df['time'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
            df = df.set_index('time')

            # Select and rename columns (CoinGecko OHLC doesn't include volume directly in this endpoint)
            # If volume is needed, use the /market_chart endpoint instead
            df = df[['open', 'high', 'low', 'close']]

            # Ensure numeric types
            df = df.apply(pd.to_numeric)

            return df

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching OHLC for {coin_id}: {e.response.status_code} - {e.response.text}")
            raise e
        except httpx.RequestError as e:
            logger.error(f"Network error fetching OHLC for {coin_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching OHLC for {coin_id}: {e}")
            return None


@cached('coingecko_market', lambda coin_id, vs_currency='usd', days=365, **kwargs: f"market_data_{coin_id}_{vs_currency}_{days}")
async def get_historical_market_data(
    coin_id: str,
    vs_currency: str = "usd",
    days: int = 365, # Fetch more data for better SMA calculation
    # Interval is typically auto-determined by CoinGecko based on 'days'
    # 'daily' for days > 90
) -> Optional[pd.DataFrame]:
    """
    Fetches historical market data (price, volume) for a coin from CoinGecko's
    /market_chart endpoint and converts it to an OHLC DataFrame.
    Results are cached to reduce API calls.

    Args:
        coin_id: The CoinGecko identifier for the coin.
        vs_currency: The target currency (default: 'usd').
        days: Number of days of historical data to fetch (default: 365).

    Returns:
        A pandas DataFrame with OHLCV data indexed by datetime, or None on error.
        Columns: 'open', 'high', 'low', 'close', 'volume'
    """
    api_url = f"{COINGECKO_API_BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": vs_currency.lower(),
        "days": str(days),
        # "interval": "daily" # Usually inferred by CoinGecko based on 'days'
    }
    logger.info(f"Fetching market chart data for {coin_id} ({days} days)...")

    async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data or 'prices' not in data or not data['prices']:
                logger.warning(f"No market chart data found for {coin_id} / {vs_currency}.")
                return None

            # Process Prices
            prices_df = pd.DataFrame(data['prices'], columns=['timestamp_ms', 'price'])
            prices_df['time'] = pd.to_datetime(prices_df['timestamp_ms'], unit='ms')
            prices_df = prices_df.set_index('time')[['price']] # Keep only price for OHLC resampling

            # Resample price data to daily OHLC
            # For daily data from market_chart, this effectively sets o=h=l=c=price
            ohlc_df = prices_df['price'].resample('D').ohlc()

            # Process Volumes (if available)
            if 'total_volumes' in data and data['total_volumes']:
                volumes_df = pd.DataFrame(data['total_volumes'], columns=['timestamp_ms', 'volume'])
                volumes_df['time'] = pd.to_datetime(volumes_df['timestamp_ms'], unit='ms')
                volumes_df = volumes_df.set_index('time')[['volume']]
                # Resample volume (summing daily volume) and join with OHLC
                daily_volumes = volumes_df['volume'].resample('D').sum()
                ohlc_df = ohlc_df.join(daily_volumes)
            else:
                ohlc_df['volume'] = 0 # Assign zero volume if not available

            # Rename columns to match indicator expectations
            ohlc_df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}, inplace=True)

            # Handle potential NaNs introduced by resampling or missing data
            ohlc_df.dropna(inplace=True) # Drop rows with any NaN to ensure indicator calculations work

            if ohlc_df.empty:
                 logger.warning(f"DataFrame became empty after processing/cleaning for {coin_id}.")
                 return None

            logger.info(f"Successfully processed market chart data into OHLCV DataFrame for {coin_id}.")
            return ohlc_df.apply(pd.to_numeric) # Ensure numeric types

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching market chart for {coin_id}: {e.response.status_code} - {e.response.text}")
            # Consider raising specific errors if needed
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error fetching market chart for {coin_id}: {e}")
            return None
        except KeyError as e:
            logger.error(f"Data format error (missing key) processing market chart for {coin_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching/processing market chart for {coin_id}: {e}")
            import traceback
            logger.error(traceback.format_exc()) # Log full traceback for debugging
            return None


# Example usage (can be removed or moved to CLI/tests)
# import asyncio
# async def main():
#     # Test get_coin_data_by_id
#     # btc_data = await get_coin_data_by_id("bitcoin")
#     # if btc_data:
#     #     print(f"Fetched data for: {btc_data.name}")
#     #     print(f"Current Price (USD): {btc_data.market_data.current_price.get('usd')}")

#     # Test get_historical_ohlc
#     ohlc_df = await get_historical_ohlc("bitcoin", days=30)
#     if ohlc_df is not None:
#         print("\n--- Historical OHLC Data (last 5 days) ---")
#         print(ohlc_df.tail())
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())
