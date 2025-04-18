import os
import httpx
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from app.utils.cache_manager import cache_manager, cached

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_BASE_URL = "https://api.perplexity.ai"

# Setup logging
logger = logging.getLogger(__name__)

@cached('perplexity', lambda query, detail_level="normal", **kwargs: f"search_{hash(query)}_{detail_level}")
async def search_perplexity(query: str, detail_level: str = "normal") -> Optional[Dict[str, Any]]:
    """
    Performs a search using the Perplexity API.

    Args:
        query: The search query string.
        detail_level: Desired level of detail ('brief', 'normal', 'detailed').

    Returns:
        A dictionary containing the search results from Perplexity, or None on error.
    """
    if not PERPLEXITY_API_KEY:
        logger.error("Error: PERPLEXITY_API_KEY not found in environment variables.")
        return None

    logger.info(f"Performing Perplexity search for query: '{query[:100]}...' (detail: {detail_level})")

    # Map detail level to model and token settings
    model = "sonar"  # Default model
    max_tokens = 500  # Default token limit

    if detail_level == "brief":
        max_tokens = 300
    elif detail_level == "detailed":
        max_tokens = 800
        model = "sonar-pro"  # Use a larger model for detailed responses

    # Prepare API request
    api_url = f"{PERPLEXITY_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that provides accurate, factual information based on web search results."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }

    # Make API call
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            # Extract the content from the response
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content")
                if content:
                    # Return a structured response
                    return {
                        "query": query,
                        "result": content,
                        "sources": result.get("links", [])  # Some Perplexity responses include sources
                    }
                else:
                    logger.warning(f"Perplexity response format unexpected: No content found")
                    return None
            else:
                logger.warning(f"Perplexity response format unexpected or empty: {result}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Perplexity search: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error during Perplexity search: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Perplexity search: {e}")
            return None


@cached('perplexity', lambda coin_name, coin_symbol, **kwargs: f"twitter_sentiment_{coin_symbol.lower()}")
async def get_twitter_sentiment_for_coin(coin_name: str, coin_symbol: str) -> Optional[Dict[str, Any]]:
    """
    Uses Perplexity search to find recent Twitter sentiment about a specific coin.

    Args:
        coin_name: The full name of the cryptocurrency (e.g., "Bitcoin").
        coin_symbol: The ticker symbol of the cryptocurrency (e.g., "BTC").

    Returns:
        A dictionary containing summarized Twitter sentiment or search results,
        or None if the search fails or returns no relevant data.
    """
    # Construct a query focused on recent Twitter discussions
    query = f"What is the recent Twitter sentiment about {coin_name} (${coin_symbol})? Look for trends, key opinions, and potential concerns mentioned in tweets from the last 24-48 hours. Format your response with these sections: 1) Overall sentiment (bullish/bearish/neutral), 2) Key themes or topics being discussed, 3) Notable tweets or opinions, 4) Any significant news affecting sentiment."

    logger.info(f"Fetching Twitter sentiment for {coin_name} ({coin_symbol}) via Perplexity...")

    search_results = await search_perplexity(query, detail_level="normal")

    if search_results:
        # Process the search results into a structured format
        result_text = search_results.get("result", "")

        # Extract overall sentiment (simple approach - can be enhanced)
        overall_sentiment = "neutral"  # Default
        if "bullish" in result_text.lower():
            overall_sentiment = "bullish"
        elif "bearish" in result_text.lower():
            overall_sentiment = "bearish"

        # Extract key tweets (simple approach - can be enhanced)
        key_tweets = []
        lines = result_text.split('\n')
        for line in lines:
            if "tweet" in line.lower() or "@" in line or '"' in line:
                # This is a simplistic approach - in a real implementation,
                # you might want more sophisticated parsing
                key_tweets.append(line.strip())

        # Create structured response
        processed_sentiment = {
            "summary": result_text,
            "key_tweets": key_tweets[:5],  # Limit to top 5 tweets
            "overall_sentiment": overall_sentiment,
            "raw_search_result": search_results  # Include the full result for reference
        }

        return processed_sentiment
    else:
        logger.warning(f"Perplexity search failed for {coin_name} Twitter sentiment.")
        return None
