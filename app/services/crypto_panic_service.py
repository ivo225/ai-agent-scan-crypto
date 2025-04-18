import os
import httpx
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from app.utils.cache_manager import cache_manager, cached

load_dotenv() # Load environment variables from .env file

CRYPTO_PANIC_API_KEY = os.getenv("CRYPTO_PANIC_API_KEY")
CRYPTO_PANIC_API_BASE_URL = "https://cryptopanic.com/api/v1"

# Setup logging
logger = logging.getLogger(__name__)

@cached('cryptopanic', lambda currency_symbol, **kwargs: f"sentiment_{currency_symbol.lower()}")
async def get_sentiment_data(currency_symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetches news and sentiment data for a specific currency from CryptoPanic API.

    Args:
        currency_symbol: The ticker symbol of the cryptocurrency (e.g., 'BTC', 'ETH').

    Returns:
        A dictionary containing the API response data if successful, None otherwise.
        Raises httpx.HTTPStatusError for API errors (4xx, 5xx).
    """
    if not CRYPTO_PANIC_API_KEY:
        logger.error("Error: CRYPTO_PANIC_API_KEY not found in environment variables.")
        return None

    logger.info(f"Fetching sentiment data for {currency_symbol} from CryptoPanic")

    api_url = f"{CRYPTO_PANIC_API_BASE_URL}/posts/"
    params = {
        "auth_token": CRYPTO_PANIC_API_KEY,
        "currencies": currency_symbol.upper(),
        "public": "true" # Fetch publicly available posts
        # Add other parameters as needed (e.g., filter, kind)
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status() # Raise exception for 4xx/5xx errors

            data = response.json()
            # Basic check for results
            if not data or "results" not in data:
                logger.warning(f"No sentiment data found for {currency_symbol} on CryptoPanic.")
                return None

            # Process the results slightly for easier consumption
            processed_data = {
                "count": data.get("count", 0),
                "results": data.get("results", []),
                # Add top 5 posts with vote details for the prompt
                "top_posts": []
            }
            if data.get("results"):
                # Sort by votes (using a simple heuristic like positive - negative, or just total)
                # CryptoPanic API doesn't provide a direct 'hotness' score easily sortable
                # Let's just take the first 5 as they appear (usually recent)
                 processed_data["top_posts"] = [
                     {
                         "title": post.get("title"),
                         "url": post.get("url"),
                         "domain": post.get("domain"),
                         "votes": post.get("votes", {}), # votes is dict: {'positive': N, 'negative': N, ...}
                         # CryptoPanic doesn't directly give sentiment classification per post easily via API
                         # We'll rely on DeepSeek to infer from title/source/votes
                     } for post in data["results"][:5]
                 ]

            return processed_data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching CryptoPanic data for {currency_symbol}: {e.response.status_code} - {e.response.text}")
            # Handle specific errors (e.g., 401 Unauthorized if key is invalid)
            raise e
        except httpx.RequestError as e:
            logger.error(f"Network error fetching CryptoPanic data for {currency_symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching CryptoPanic data for {currency_symbol}: {e}")
            return None

# Example usage (can be removed or moved to CLI/tests)
# import asyncio
# async def main():
#     sentiment = await get_sentiment_data("BTC")
#     if sentiment:
#         print(f"Fetched {sentiment.get('count', 0)} posts for BTC.")
#         # print(sentiment['results'][0]) # Print first post details
#
# if __name__ == "__main__":
#     asyncio.run(main())
