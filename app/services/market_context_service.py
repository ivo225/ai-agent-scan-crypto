import httpx
from typing import Optional, Dict, Any

# Configuration Constants
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
FEAR_GREED_INDEX_URL = "https://api.alternative.me/fng/?limit=1" # Fetch only the latest value

# Use a shared async client for efficiency
_client = httpx.AsyncClient(timeout=15.0) # Shared client with reasonable timeout

async def get_global_market_data() -> Optional[Dict[str, Any]]:
    """
    Fetches global cryptocurrency market data from CoinGecko.

    Returns:
        A dictionary containing global market data, or None on error.
        Keys might include: total_market_cap, total_volume, market_cap_percentage,
        market_cap_change_percentage_24h_usd, etc.
    """
    try:
        response = await _client.get(COINGECKO_GLOBAL_URL)
        response.raise_for_status() # Raise exception for 4xx/5xx errors
        data = response.json()
        # The actual data is nested under the 'data' key
        return data.get("data")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching CoinGecko global data: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"Network error fetching CoinGecko global data: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred fetching CoinGecko global data: {e}")
        return None

async def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """
    Fetches the latest Fear & Greed Index data from Alternative.me.

    Returns:
        A dictionary containing the latest F&G data, or None on error.
        Keys typically include: value, value_classification, timestamp.
    """
    try:
        response = await _client.get(FEAR_GREED_INDEX_URL)
        response.raise_for_status()
        data = response.json()
        # The actual data points are in the first item of the 'data' list
        if data and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            return data["data"][0]
        else:
            print(f"Unexpected format received from Fear & Greed API: {data}")
            return None
    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching Fear & Greed Index: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"Network error fetching Fear & Greed Index: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred fetching Fear & Greed Index: {e}")
        return None

async def get_market_context() -> Dict[str, Optional[Any]]:
    """
    Fetches and combines global market data and Fear & Greed Index.

    Returns:
        A dictionary containing combined market context data. Keys will be 'global_market'
        and 'fear_greed'. Values will be the fetched data dictionaries or None if fetching failed.
    """
    print("Fetching market context (Global Data & Fear/Greed)...")
    global_data = await get_global_market_data()
    fear_greed_data = await get_fear_greed_index()

    return {
        "global_market": global_data,
        "fear_greed": fear_greed_data,
    }

# Example usage (for testing)
# import asyncio
#
# async def main():
#     context = await get_market_context()
#     print("\n--- Market Context ---")
#     print(f"Global Market Data: {context.get('global_market')}")
#     print(f"Fear & Greed Index: {context.get('fear_greed')}")
#
# if __name__ == "__main__":
#     asyncio.run(main())
