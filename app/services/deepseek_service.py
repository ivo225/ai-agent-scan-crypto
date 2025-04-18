import os
import httpx
import pandas as pd # Import pandas for isna()
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from app.models.coin import CoinData # To type hint input data

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# Assuming a chat completions endpoint, adjust if DeepSeek uses a different one
DEEPSEEK_API_BASE_URL = "https://api.deepseek.com/v1" # Verify this URL

async def get_deepseek_analysis(
    coin_data: CoinData,
    sentiment_data: Optional[Dict[str, Any]] = None, # CryptoPanic news
    technical_indicators: Optional[Dict[str, Optional[float]]] = None,
    market_context: Optional[Dict[str, Any]] = None,
    twitter_sentiment: Optional[Dict[str, Any]] = None # Add Twitter sentiment parameter
) -> Optional[str]:
    """
    Uses DeepSeek API to analyze cryptocurrency data, including technical indicators, news sentiment,
    Twitter sentiment, market context, and generate insights with price predictions.
    market context, and generate insights with price predictions.

    Args:
        coin_data: CoinData object containing market and descriptive info.
        coin_data: CoinData object containing market and descriptive info.
        sentiment_data: Optional dictionary containing CryptoPanic sentiment/news data.
        technical_indicators: Optional dictionary containing calculated technical indicator values.
        market_context: Optional dictionary containing 'global_market' and 'fear_greed' data.
        twitter_sentiment: Optional dictionary containing summarized Twitter sentiment from Perplexity.

    Returns:
        A string containing the detailed analysis and price prediction from DeepSeek, or None on error.
        Raises httpx.HTTPStatusError for API errors (4xx, 5xx).
    """
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY not found in environment variables.")
        return None

    api_url = f"{DEEPSEEK_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    # --- Construct the Prompt ---
    prompt_lines = [
        f"Analyze the cryptocurrency '{coin_data.name}' ({coin_data.symbol.upper()}).",
        f"Current Price (USD): {coin_data.market_data.current_price.get('usd', 'N/A')}",
        f"Market Cap (USD): {coin_data.market_data.market_cap.get('usd', 'N/A')}",
        f"24h Volume (USD): {coin_data.market_data.total_volume.get('usd', 'N/A')}",

        "\nPrice Changes:",
        f"1h:  {f'{coin_data.market_data.price_change_percentage_1h:.2f}%' if hasattr(coin_data.market_data, 'price_change_percentage_1h') and coin_data.market_data.price_change_percentage_1h is not None else 'N/A'}",
        f"24h: {f'{coin_data.market_data.price_change_percentage_24h:.2f}%' if hasattr(coin_data.market_data, 'price_change_percentage_24h') and coin_data.market_data.price_change_percentage_24h is not None else 'N/A'}",
        f"7d:  {f'{coin_data.market_data.price_change_percentage_7d:.2f}%' if hasattr(coin_data.market_data, 'price_change_percentage_7d') and coin_data.market_data.price_change_percentage_7d is not None else 'N/A'}",
        f"30d: {f'{coin_data.market_data.price_change_percentage_30d:.2f}%' if hasattr(coin_data.market_data, 'price_change_percentage_30d') and coin_data.market_data.price_change_percentage_30d is not None else 'N/A'}",

        f"\nDescription: {coin_data.description.get('en', 'N/A')[:500]}..." # Limit description length
    ]

    # Add Enhanced Market Context
    if market_context:
        prompt_lines.append("\nEnhanced Market Context:")

        # Extract all market context components
        fg_data = market_context.get('fear_greed')
        fg_trend_data = market_context.get('fear_greed_trend')
        gm_data = market_context.get('global_market')
        volatility_data = market_context.get('market_volatility')
        btc_dominance_data = market_context.get('btc_dominance')

        # Current Fear & Greed Index
        if fg_data:
            prompt_lines.append(f"- Fear & Greed Index: {fg_data.get('value', 'N/A')} ({fg_data.get('value_classification', 'N/A')})")

        # Fear & Greed Trend
        if fg_trend_data:
            trend = fg_trend_data.get('trend', 'unknown')
            trend_direction = fg_trend_data.get('trend_direction', 'unknown')
            avg_value = fg_trend_data.get('avg_value', 'N/A')
            prompt_lines.append(f"- Fear & Greed Trend (30d): {trend.replace('_', ' ')} ({trend_direction.replace('_', ' ')}), avg: {avg_value}")

        # Global Market Data
        if gm_data:
            mkt_cap_change = gm_data.get('market_cap_change_percentage_24h_usd')
            btc_dom = gm_data.get('market_cap_percentage', {}).get('btc')
            prompt_lines.append(f"- Global Market Cap Change (24h): {f'{mkt_cap_change:.2f}%' if mkt_cap_change is not None else 'N/A'}")

        # Market Volatility
        if volatility_data:
            volatility_pattern = volatility_data.get('volatility_pattern', 'unknown')
            avg_volatility_24h = volatility_data.get('avg_volatility_24h', 'N/A')
            prompt_lines.append(f"- Market Volatility: {volatility_pattern.replace('_', ' ')} ({avg_volatility_24h}% 24h)")

        # BTC Dominance Analysis
        if btc_dominance_data:
            btc_dominance = btc_dominance_data.get('btc_dominance', 'N/A')
            dominance_level = btc_dominance_data.get('dominance_level', 'unknown')
            market_implication = btc_dominance_data.get('market_implication', 'unknown')
            btc_eth_ratio = btc_dominance_data.get('btc_eth_ratio', 'N/A')
            prompt_lines.append(f"- BTC Dominance: {btc_dominance:.2f}% ({dominance_level.replace('_', ' ')})")
            prompt_lines.append(f"- Market Implication: {market_implication.replace('_', ' ')}")
            prompt_lines.append(f"- BTC/ETH Ratio: {btc_eth_ratio:.2f}")

    # Add Sentiment Analysis Data
    if sentiment_data and sentiment_data.get("top_posts"):
        prompt_lines.append("\nRecent News/Sentiment Highlights (Top 5):")
        for post in sentiment_data["top_posts"]:
            votes = post.get('votes', {})
            vote_summary = f"👍{votes.get('positive', 0)} 👎{votes.get('negative', 0)}" # Compact vote summary
            prompt_lines.append(f"- {post.get('title', 'No Title')} ({post.get('domain', 'N/A')}) - Votes: {vote_summary}")
    elif sentiment_data:
        prompt_lines.append(f"\nRecent News Count (CryptoPanic): {sentiment_data.get('count', 0)}")

    # Add Twitter Sentiment Analysis Data (from Perplexity)
    if twitter_sentiment:
        prompt_lines.append("\nRecent Twitter Sentiment Highlights (via Perplexity):")
        # TODO: Adjust keys based on the actual structure returned by the MCP tool/perplexity_service
        summary = twitter_sentiment.get('summary', 'No summary available.')
        key_tweets = twitter_sentiment.get('key_tweets', [])
        overall = twitter_sentiment.get('overall_sentiment', 'neutral')
        prompt_lines.append(f"- Overall Trend: {overall.capitalize()}")
        prompt_lines.append(f"- Summary: {summary}")
        if key_tweets:
             prompt_lines.append("- Key Tweets/Themes:")
             for tweet in key_tweets[:3]: # Limit to a few examples
                 prompt_lines.append(f"  - {tweet}") # Adjust formatting as needed
    else:
        # Explicitly state if Twitter data wasn't available for the prompt
        prompt_lines.append("\nRecent Twitter Sentiment Highlights (via Perplexity): Data not available.")


    # Add technical analysis data if available
    if technical_indicators:
        prompt_lines.append("\nTechnical Indicators:")
        # Use 6 decimal places for precision, handle None/NaN
        def fmt_ind(val): return f"{val:.6f}" if not pd.isna(val) else "N/A"

        prompt_lines.append(f"- RSI (14): {fmt_ind(technical_indicators.get('rsi'))}")
        prompt_lines.append(f"- MACD (8, 17, 9): {fmt_ind(technical_indicators.get('macd'))}")
        prompt_lines.append(f"- MACD Signal: {fmt_ind(technical_indicators.get('macd_signal'))}")
        prompt_lines.append(f"- MACD Histogram: {fmt_ind(technical_indicators.get('macd_hist'))}")
        prompt_lines.append(f"- SMA 50: {fmt_ind(technical_indicators.get('sma_50'))}")
        # prompt_lines.append(f"- SMA 200: {fmt_ind(technical_indicators.get('sma_200'))}") # Removed
        prompt_lines.append(f"- Bollinger Upper: {fmt_ind(technical_indicators.get('bb_upper'))}")
        prompt_lines.append(f"- Bollinger Middle: {fmt_ind(technical_indicators.get('bb_middle'))}")
        prompt_lines.append(f"- Bollinger Lower: {fmt_ind(technical_indicators.get('bb_lower'))}")

    # Add confidence data to the prompt
    if technical_indicators and technical_indicators.get('confidence'):
        confidence = technical_indicators.get('confidence', {})
        score = confidence.get('overall_score', 0)
        direction = confidence.get('direction', 'neutral')
        supporting = confidence.get('supporting_indicators', [])
        conflicting = confidence.get('conflicting_indicators', [])

        prompt_lines.append(f"\nPrediction Confidence Assessment:")
        prompt_lines.append(f"- Overall Confidence Score: {score}/100 ({direction.upper()})")
        if supporting:
            prompt_lines.append(f"- Supporting Signals: {', '.join(supporting)}")
        if conflicting:
             prompt_lines.append(f"- Conflicting Signals: {', '.join(conflicting)}")


    prompt_lines.append("\nBased on all the above data (individual coin market/news/twitter/technicals, enhanced market context, confidence assessment):")
    prompt_lines.append("1. Provide a detailed short-term price prediction (1-4 weeks) with potential price targets (low/high range) and key support/resistance levels. Consider the enhanced market context (F&G trend, volatility, BTC dominance), Twitter sentiment trends, and calibrate certainty based on the confidence score.")
    prompt_lines.append("2. Provide a detailed long-term price prediction (3-12 months) with potential price targets (low/high range). Consider the enhanced market context, fundamental description, and calibrate certainty based on the confidence score.")
    prompt_lines.append("3. Briefly explain how the technical indicators, enhanced market context (especially F&G trend, market volatility, and BTC dominance), AND Twitter sentiment support your predictions.")
    prompt_lines.append("4. Analyze how the current news sentiment (CryptoPanic) AND Twitter sentiment might impact price action (consider if priced in, potential catalysts/reversals, divergences).")
    prompt_lines.append("5. Suggest potential entry price points based on the combined analysis, with specific attention to market volatility patterns.")
    prompt_lines.append("6. Summarize the overall outlook and confidence level (Low/Medium/High), explicitly mentioning the influence of both Twitter sentiment and enhanced market context.")


    prompt = "\n".join(prompt_lines)

    # --- Prepare Request Body ---
    # Adjust model name if needed (e.g., 'deepseek-coder', 'deepseek-chat')
    # --- Enhanced System Prompt ---
    system_prompt = (
        "You are an expert cryptocurrency market analyst. Your analysis integrates market data, "
        "sentiment (news & Twitter), enhanced market context, and technical indicators (RSI, MACD, SMA, Bollinger Bands). Provide structured, "
        "actionable insights including specific price targets, support/resistance levels, and time horizons. "
        "Explain the reasoning based on the provided data, explicitly mentioning how Twitter sentiment and market context influence the outlook. Be concise and do not ask follow-up questions."
        "\n\n**Important:** Critically evaluate news sentiment regarding exchange listings. Verify if the coin is already listed on major exchanges (e.g., Binance, Coinbase, OKX) before suggesting a listing as a future catalyst."
        "\n\nIndicator Interpretation Guide:"
        "\n- RSI: >70 Overbought, <30 Oversold."
        "\n- MACD: Line/Signal crossovers and histogram divergence indicate momentum shifts."
        "\n- SMA 50: Price vs SMA 50 shows short/medium-term trend."
        "\n- Bollinger Bands: Price near upper/lower bands suggests volatility and potential reversals. Middle band acts as dynamic support/resistance."
        "\n\nMarket Context Interpretation Guide:"
        "\n- Fear & Greed Trend: Consider both current value and trend direction. Extreme fear with increasing trend often signals bottoming."
        "\n- Market Volatility: High volatility strengthens directional signals but increases risk. Low volatility often precedes breakouts."
        "\n- BTC Dominance: High dominance often bearish for altcoins. Low dominance typically bullish for altcoins."
        "\n- BTC/ETH Ratio: Indicates money flow between top cryptos and can signal broader market rotation patterns."
        "\n\nSentiment Analysis Guide:"
        "\n- Consider news source (CryptoPanic) and Twitter trends (Perplexity)."
        "\n- Evaluate if sentiment is already priced in or could be a future catalyst."
        "\n- Note sentiment/price divergences across both news and Twitter."
        "\n\nConfidence Score Guide:"
        "\n- High Confidence (70+): Use strong conviction language (e.g., 'likely', 'expected'). Narrower price target ranges."
        "\n- Medium Confidence (40-69): Use cautious language (e.g., 'potential', 'could'). Wider price target ranges."
        "\n- Low Confidence (<40): Emphasize uncertainty. Present multiple scenarios. Very wide or no specific price targets."
    )


    payload = {
        "model": "deepseek-chat", # Verify the correct model identifier
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500, # Increased max_tokens for more detailed analysis
        "temperature": 0.6, # Slightly lower temperature for more focused analysis
    }

    # --- Make API Call ---
    async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout for AI generation
        try:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()

            # Extract the analysis from the response
            if result and "choices" in result and len(result["choices"]) > 0:
                analysis = result["choices"][0].get("message", {}).get("content")
                if analysis:
                    return analysis.strip()
                else:
                    print(f"DeepSeek response format unexpected: No content found in choices[0].message")
                    return None
            else:
                print(f"DeepSeek response format unexpected or empty: {result}")
                return None

        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching DeepSeek analysis for {coin_data.symbol}: {e.response.status_code} - {e.response.text}")
            raise e
        except httpx.RequestError as e:
            print(f"Network error fetching DeepSeek analysis for {coin_data.symbol}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred fetching DeepSeek analysis for {coin_data.symbol}: {e}")
            return None


async def get_deepseek_chat_response(message: str, history: List[Dict[str, str]] = None) -> Optional[str]:
    """
    Sends a general chat message to the DeepSeek API and returns the response.

    Args:
        message: The user's message.
        history: Optional list of previous messages for context (e.g., [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]).

    Returns:
        The chat response from DeepSeek, or None on error.
        Raises httpx.HTTPStatusError for API errors (4xx, 5xx).
    """
    if not DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY not found in environment variables.")
        return None

    api_url = f"{DEEPSEEK_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    # Basic system prompt for general chat
    system_prompt = "You are a helpful assistant integrated into a crypto analysis tool. Be concise and helpful."
    messages = [{"role": "system", "content": system_prompt}]

    # Add history if provided
    if history:
        messages.extend(history)

    # Add the current user message
    messages.append({"role": "user", "content": message})

    payload = {
        "model": "deepseek-chat", # Use the chat model
        "messages": messages,
        "max_tokens": 150, # Keep responses relatively short for chat
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if result and "choices" in result and len(result["choices"]) > 0:
                chat_response = result["choices"][0].get("message", {}).get("content")
                return chat_response.strip() if chat_response else None
            else:
                print(f"DeepSeek chat response format unexpected or empty: {result}")
                return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error during DeepSeek chat: {e.response.status_code} - {e.response.text}")
            raise e # Re-raise to be handled by caller if needed
        except httpx.RequestError as e:
            print(f"Network error during DeepSeek chat: {e}")
            return None # Return None on network errors
        except Exception as e:
            print(f"An unexpected error occurred during DeepSeek chat: {e}")
            return None # Return None on other errors


# Example usage (can be removed or moved to CLI/tests)
# import asyncio
# from app.services.coin_gecko_service import get_coin_data_by_id
#
# async def main():
#     coin_data = await get_coin_data_by_id("bitcoin")
#     if coin_data:
#         analysis = await get_deepseek_analysis(coin_data)
#         if analysis:
#             print("\n--- DeepSeek Analysis ---")
#             print(analysis)
#         else:
#             print("Could not get analysis from DeepSeek.")
#
# if __name__ == "__main__":
#     asyncio.run(main())
