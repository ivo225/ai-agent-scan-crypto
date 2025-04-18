import httpx
import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from app.utils.cache_manager import cache_manager, cached

# Configuration Constants
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
FEAR_GREED_INDEX_URL = "https://api.alternative.me/fng/?limit=1" # Fetch only the latest value
FEAR_GREED_HISTORY_URL = "https://api.alternative.me/fng/?limit=30" # For trend analysis
COINGECKO_COINS_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Setup logging
logger = logging.getLogger(__name__)

# Use a shared async client for efficiency
_client = httpx.AsyncClient(timeout=15.0) # Shared client with reasonable timeout

@cached('market_context', lambda **kwargs: "global_market_data")
async def get_global_market_data() -> Optional[Dict[str, Any]]:
    """
    Fetches global cryptocurrency market data from CoinGecko.

    Returns:
        A dictionary containing global market data, or None on error.
        Keys might include: total_market_cap, total_volume, market_cap_percentage,
        market_cap_change_percentage_24h_usd, etc.
    """
    logger.info("Fetching global market data from CoinGecko")
    try:
        response = await _client.get(COINGECKO_GLOBAL_URL)
        response.raise_for_status() # Raise exception for 4xx/5xx errors
        data = response.json()
        # The actual data is nested under the 'data' key
        return data.get("data")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching CoinGecko global data: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Network error fetching CoinGecko global data: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching CoinGecko global data: {e}")
        return None

@cached('market_context', lambda **kwargs: "fear_greed_index")
async def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """
    Fetches the latest Fear & Greed Index data from Alternative.me.

    Returns:
        A dictionary containing the latest F&G data, or None on error.
        Keys typically include: value, value_classification, timestamp.
    """
    logger.info("Fetching Fear & Greed Index from Alternative.me")
    try:
        response = await _client.get(FEAR_GREED_INDEX_URL)
        response.raise_for_status()
        data = response.json()
        # The actual data points are in the first item of the 'data' list
        if data and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            return data["data"][0]
        else:
            logger.warning(f"Unexpected format received from Fear & Greed API: {data}")
            return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching Fear & Greed Index: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Network error fetching Fear & Greed Index: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching Fear & Greed Index: {e}")
        return None

@cached('market_context', lambda **kwargs: "fear_greed_trend")
async def get_fear_greed_trend() -> Optional[Dict[str, Any]]:
    """
    Fetches the Fear & Greed Index trend data (last 30 days) from Alternative.me.

    Returns:
        A dictionary containing trend analysis of F&G data, or None on error.
        Keys include: 'trend', 'avg_value', 'min_value', 'max_value', 'trend_direction'.
    """
    logger.info("Fetching Fear & Greed Index trend from Alternative.me")
    try:
        response = await _client.get(FEAR_GREED_HISTORY_URL)
        response.raise_for_status()
        data = response.json()

        # The historical data points are in the 'data' list
        if data and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            # Convert to pandas DataFrame for easier analysis
            fg_data = data["data"]
            values = [int(item.get("value", 0)) for item in fg_data]

            # Calculate trend metrics
            avg_value = sum(values) / len(values) if values else 0
            min_value = min(values) if values else 0
            max_value = max(values) if values else 0

            # Determine trend direction (using linear regression slope)
            if len(values) >= 7:  # Use at least a week of data
                # Get the last 7 days for recent trend
                recent_values = values[:7]  # Data is in reverse chronological order
                x = np.arange(len(recent_values))
                slope, _ = np.polyfit(x, recent_values, 1)

                if slope > 1.0:
                    trend_direction = "strongly_increasing"
                elif slope > 0.3:
                    trend_direction = "increasing"
                elif slope < -1.0:
                    trend_direction = "strongly_decreasing"
                elif slope < -0.3:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "unknown"

            # Determine overall market sentiment trend
            if avg_value >= 75:
                trend = "extreme_greed"
            elif avg_value >= 60:
                trend = "greed"
            elif avg_value <= 25:
                trend = "extreme_fear"
            elif avg_value <= 40:
                trend = "fear"
            else:
                trend = "neutral"

            return {
                "trend": trend,
                "avg_value": round(avg_value, 1),
                "min_value": min_value,
                "max_value": max_value,
                "trend_direction": trend_direction,
                "raw_values": values[:7]  # Include the last 7 days of raw values
            }
        else:
            logger.warning(f"Unexpected format received from Fear & Greed History API: {data}")
            return None
    except Exception as e:
        logger.error(f"An error occurred fetching Fear & Greed trend: {e}")
        return None

@cached('market_context', lambda coin_id=None, **kwargs: f"market_volatility_{coin_id if coin_id else 'global'}")
async def get_market_volatility(coin_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Calculates market volatility metrics for a specific coin or the global market.

    Args:
        coin_id: Optional CoinGecko ID for a specific coin. If None, calculates for top coins.

    Returns:
        Dictionary with volatility metrics or None on error.
    """
    logger.info(f"Calculating market volatility for {'global market' if coin_id is None else coin_id}")

    try:
        # If no specific coin, get data for top 10 coins
        if coin_id is None:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "10",
                "page": "1",
                "sparkline": "true",  # This gives 7d price data
                "price_change_percentage": "1h,24h,7d"
            }
            response = await _client.get(COINGECKO_COINS_MARKETS_URL, params=params)
            response.raise_for_status()
            coins_data = response.json()

            if not coins_data or not isinstance(coins_data, list):
                logger.warning("Invalid or empty response from CoinGecko markets endpoint")
                return None

            # Calculate average volatility across top coins
            volatility_24h = [abs(coin.get('price_change_percentage_24h', 0) or 0) for coin in coins_data]
            volatility_7d = [abs(coin.get('price_change_percentage_7d', 0) or 0) for coin in coins_data]

            # Calculate volatility metrics
            avg_volatility_24h = sum(volatility_24h) / len(volatility_24h) if volatility_24h else 0
            avg_volatility_7d = sum(volatility_7d) / len(volatility_7d) if volatility_7d else 0
            max_volatility_24h = max(volatility_24h) if volatility_24h else 0

            # Analyze 7d sparkline data for volatility pattern
            volatility_pattern = "unknown"
            if all(coin.get('sparkline_in_7d', {}).get('price') for coin in coins_data):
                # Calculate average daily change across top coins
                daily_changes = []
                for coin in coins_data:
                    prices = coin.get('sparkline_in_7d', {}).get('price', [])
                    if len(prices) >= 7:
                        # Calculate daily percentage changes
                        changes = [abs((prices[i] - prices[i-1]) / prices[i-1] * 100) for i in range(1, 7)]
                        daily_changes.append(sum(changes) / len(changes))

                avg_daily_change = sum(daily_changes) / len(daily_changes) if daily_changes else 0

                # Determine volatility pattern
                if avg_daily_change > 5.0:
                    volatility_pattern = "highly_volatile"
                elif avg_daily_change > 3.0:
                    volatility_pattern = "volatile"
                elif avg_daily_change > 1.5:
                    volatility_pattern = "moderate"
                else:
                    volatility_pattern = "stable"

            return {
                "avg_volatility_24h": round(avg_volatility_24h, 2),
                "avg_volatility_7d": round(avg_volatility_7d, 2),
                "max_volatility_24h": round(max_volatility_24h, 2),
                "volatility_pattern": volatility_pattern
            }

        # For specific coin (simplified implementation)
        else:
            params = {
                "vs_currency": "usd",
                "ids": coin_id,
                "sparkline": "true",
                "price_change_percentage": "1h,24h,7d"
            }
            response = await _client.get(COINGECKO_COINS_MARKETS_URL, params=params)
            response.raise_for_status()
            coins_data = response.json()

            if not coins_data or not isinstance(coins_data, list) or len(coins_data) == 0:
                logger.warning(f"No data found for coin {coin_id}")
                return None

            coin_data = coins_data[0]
            volatility_24h = abs(coin_data.get('price_change_percentage_24h', 0) or 0)
            volatility_7d = abs(coin_data.get('price_change_percentage_7d', 0) or 0)

            # Analyze 7d sparkline data for volatility pattern
            volatility_pattern = "unknown"
            prices = coin_data.get('sparkline_in_7d', {}).get('price', [])
            if len(prices) >= 7:
                # Calculate daily percentage changes
                changes = [abs((prices[i] - prices[i-1]) / prices[i-1] * 100) for i in range(1, 7)]
                avg_daily_change = sum(changes) / len(changes) if changes else 0

                # Determine volatility pattern
                if avg_daily_change > 5.0:
                    volatility_pattern = "highly_volatile"
                elif avg_daily_change > 3.0:
                    volatility_pattern = "volatile"
                elif avg_daily_change > 1.5:
                    volatility_pattern = "moderate"
                else:
                    volatility_pattern = "stable"

            return {
                "volatility_24h": round(volatility_24h, 2),
                "volatility_7d": round(volatility_7d, 2),
                "volatility_pattern": volatility_pattern
            }

    except Exception as e:
        logger.error(f"Error calculating market volatility: {e}")
        return None

@cached('market_context', lambda coin_id=None, **kwargs: f"btc_dominance_trend")
async def get_btc_dominance_trend() -> Optional[Dict[str, Any]]:
    """
    Analyzes Bitcoin dominance trend based on current and historical data.

    Returns:
        Dictionary with BTC dominance trend analysis or None on error.
    """
    logger.info("Analyzing Bitcoin dominance trend")

    try:
        # Get current global market data for BTC dominance
        global_data = await get_global_market_data()
        if not global_data or not isinstance(global_data.get('market_cap_percentage'), dict):
            logger.warning("Invalid or missing market cap percentage data")
            return None

        btc_dominance = global_data['market_cap_percentage'].get('btc', 0)
        eth_dominance = global_data['market_cap_percentage'].get('eth', 0)

        # Determine dominance trend based on current values
        # These thresholds are based on historical patterns
        if btc_dominance > 60:
            dominance_level = "very_high"
            market_implication = "altcoin_bearish"
        elif btc_dominance > 50:
            dominance_level = "high"
            market_implication = "slightly_altcoin_bearish"
        elif btc_dominance > 40:
            dominance_level = "moderate"
            market_implication = "neutral"
        elif btc_dominance > 30:
            dominance_level = "low"
            market_implication = "slightly_altcoin_bullish"
        else:
            dominance_level = "very_low"
            market_implication = "altcoin_bullish"

        # Calculate BTC to ETH ratio (indicator of money flow between top cryptos)
        btc_eth_ratio = btc_dominance / eth_dominance if eth_dominance > 0 else 0

        # Interpret the ratio
        if btc_eth_ratio > 4.0:
            ratio_interpretation = "strongly_btc_favored"
        elif btc_eth_ratio > 3.0:
            ratio_interpretation = "btc_favored"
        elif btc_eth_ratio > 2.0:
            ratio_interpretation = "moderately_btc_favored"
        else:
            ratio_interpretation = "balanced_or_eth_favored"

        return {
            "btc_dominance": round(btc_dominance, 2),
            "eth_dominance": round(eth_dominance, 2),
            "dominance_level": dominance_level,
            "market_implication": market_implication,
            "btc_eth_ratio": round(btc_eth_ratio, 2),
            "ratio_interpretation": ratio_interpretation
        }

    except Exception as e:
        logger.error(f"Error analyzing BTC dominance trend: {e}")
        return None

@cached('market_context', lambda **kwargs: "full_market_context")
async def get_market_context() -> Dict[str, Optional[Any]]:
    """
    Fetches and combines comprehensive market context data including:
    - Global market data
    - Fear & Greed Index (current and trend)
    - Market volatility metrics
    - Bitcoin dominance trend

    Returns:
        A dictionary containing combined market context data.
    """
    logger.info("Fetching comprehensive market context data...")

    # Fetch all context data concurrently
    global_data = await get_global_market_data()
    fear_greed_data = await get_fear_greed_index()
    fear_greed_trend_data = await get_fear_greed_trend()
    market_volatility_data = await get_market_volatility()
    btc_dominance_data = await get_btc_dominance_trend()

    return {
        "global_market": global_data,
        "fear_greed": fear_greed_data,
        "fear_greed_trend": fear_greed_trend_data,
        "market_volatility": market_volatility_data,
        "btc_dominance": btc_dominance_data
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
