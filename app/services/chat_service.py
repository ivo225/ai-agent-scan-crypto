import re
import asyncio
from typing import Tuple, Optional, Dict, Any

# Import necessary models and services (will be refined later)
from app.models.chat import ChatMessageRequest, ChatMessageResponse
# Need to import or refactor analysis logic from cli.py or its underlying services
# from app.cli import _fetch_analyze_and_save # Example - needs refactoring
from app.services.coin_gecko_service import get_coin_data_by_id, get_coin_id_from_symbol
from app.services.crypto_panic_service import get_sentiment_data
from app.services.technical_analysis_service import get_technical_analysis
# Import necessary services
from app.services.coin_gecko_service import get_coin_data_by_id, get_coin_id_from_symbol
from app.services.crypto_panic_service import get_sentiment_data
from app.services.technical_analysis_service import get_technical_analysis
from app.services.deepseek_service import get_deepseek_analysis, get_deepseek_chat_response
from app.services.perplexity_service import get_twitter_sentiment_for_coin # Import the new service
from app.db.database import AsyncSessionLocal
from app.db.repositories import report_repository
from app.models.coin import CoinData, CoinReportSchema
# Confidence calculation is handled within technical_analysis_service

# Regex to detect the analyze command and capture the coin identifier
# Allows "analyze", "analyse", case-insensitive, followed by the identifier
ANALYZE_COMMAND_PATTERN = re.compile(r"^\s*(?:analyze|analyse)\s+([a-zA-Z0-9\-]+)\s*$", re.IGNORECASE)

async def _run_analysis_for_chat(coin_identifier: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Refactored analysis logic suitable for API/chat usage.
    Fetches data, performs analysis, saves report, and returns formatted results.

    Args:
        coin_identifier: The CoinGecko ID or Ticker Symbol.

    Returns:
        A tuple containing:
        - A formatted string summary of the analysis (or error message).
        - A dictionary containing the raw/structured analysis data (or None on error).
    """
    actual_coin_id = coin_identifier
    is_symbol = bool(re.match(r"^[a-zA-Z0-9]{1,10}$", coin_identifier)) and '-' not in coin_identifier

    if is_symbol:
        print(f"Identifier '{coin_identifier}' looks like a symbol. Resolving...")
        resolved_id = await get_coin_id_from_symbol(coin_identifier)
        if resolved_id:
            actual_coin_id = resolved_id
            print(f"Resolved to ID: {actual_coin_id}")
        else:
            error_msg = f"Error: Could not resolve symbol '{coin_identifier}' to a CoinGecko ID. Please use the full ID (e.g., 'bitcoin')."
            print(error_msg)
            return error_msg, None

    print(f"Starting analysis for ID: {actual_coin_id}...")
    db_session = AsyncSessionLocal()
    tech_analysis_results = None
    sentiment_data_results = None
    twitter_sentiment_results = None # Add placeholder for Twitter data
    deepseek_analysis_result = None
    coin_data_result = None
    formatted_output = ""
    analysis_data = {}

    try:
        # 1. Fetch Base Coin Data
        coin_data_result = await get_coin_data_by_id(actual_coin_id)
        if not coin_data_result:
            error_msg = f"Error: Could not retrieve base data for '{actual_coin_id}'."
            print(error_msg)
            return error_msg, None
        analysis_data['coin_info'] = coin_data_result.dict() # Store basic info

        # 2. Fetch Sentiment Data
        sentiment_data_results = await get_sentiment_data(coin_data_result.symbol)
        analysis_data['sentiment'] = sentiment_data_results # CryptoPanic news sentiment

        # 3. Fetch Twitter Sentiment via Perplexity API
        twitter_sentiment_results = await get_twitter_sentiment_for_coin(
            coin_name=coin_data_result.name,
            coin_symbol=coin_data_result.symbol
        )
        analysis_data['twitter_sentiment'] = twitter_sentiment_results

        # 4. Perform Technical Analysis
        tech_analysis_results = await get_technical_analysis(actual_coin_id, days=90)
        if tech_analysis_results is None:
            print("Warning: Technical analysis failed or returned no data.")
            # Continue without TA data
        analysis_data['technical_analysis'] = tech_analysis_results

        # 5. Get DeepSeek Analysis with all data including Twitter sentiment
        deepseek_analysis_result = await get_deepseek_analysis(
            coin_data=coin_data_result,
            sentiment_data=sentiment_data_results, # CryptoPanic data
            technical_indicators=tech_analysis_results,
            twitter_sentiment=twitter_sentiment_results
        )
        analysis_data['ai_analysis'] = deepseek_analysis_result

        # 5. Format Results for Chat
        formatted_output += f"Analysis for {coin_data_result.name} ({coin_data_result.symbol.upper()}):\n"
        md = coin_data_result.market_data
        usd = "usd"
        formatted_output += f"- Price: ${_format_currency_chat(md.current_price.get(usd))}\n"
        formatted_output += f"- 24h Change: {md.price_change_percentage_24h:.2f}%\n" if md.price_change_percentage_24h is not None else "- 24h Change: N/A\n"

        if tech_analysis_results:
             formatted_output += "\nTechnical Indicators:\n"
             def fmt_ind(val): return f"{val:.2f}" if val is not None else "N/A"
             formatted_output += f"- RSI: {fmt_ind(tech_analysis_results.get('rsi'))}\n"
             formatted_output += f"- MACD Hist: {fmt_ind(tech_analysis_results.get('macd_hist'))}\n"
             formatted_output += f"- SMA 50: {fmt_ind(tech_analysis_results.get('sma_50'))}\n"
             if tech_analysis_results.get('confidence'):
                 conf = tech_analysis_results['confidence']
                 score = conf.get('overall_score')
                 direction = conf.get('direction', 'neutral').capitalize()
                 score_display = f"{score}/100" if score is not None else "N/A"
                 formatted_output += f"- Confidence: {score_display} ({direction})\n"

        if sentiment_data_results:
            formatted_output += f"\nNews Sentiment (CryptoPanic): {sentiment_data_results.get('count', 0)} articles\n"

        # Add Twitter Sentiment section
        if twitter_sentiment_results:
            overall = twitter_sentiment_results.get('overall_sentiment', 'neutral').capitalize()
            key_tweets = twitter_sentiment_results.get('key_tweets', [])
            formatted_output += f"\nTwitter Sentiment (Perplexity): {overall}\n"
            if key_tweets:
                formatted_output += "Key themes/tweets:\n"
                for i, tweet in enumerate(key_tweets[:3], 1):  # Show up to 3 key tweets
                    formatted_output += f"{i}. {tweet[:100]}...\n"
        else:
            formatted_output += "\nTwitter Sentiment (Perplexity): Not available.\n"


        if deepseek_analysis_result:
            formatted_output += f"\nAI Analysis Summary:\n{deepseek_analysis_result[:300]}...\n" # Truncate for chat
        else:
            formatted_output += "\nAI Analysis: Not available.\n"

        # 6. Save Report (Background task or silent save)
        # Consider making saving optional or configurable for chat
        report_to_save = CoinReportSchema(
            coin_id=coin_data_result.id,
            prediction=deepseek_analysis_result,
            # ... (populate other fields as in cli.py) ...
             rsi=tech_analysis_results.get('rsi') if tech_analysis_results else None,
             macd=tech_analysis_results.get('macd') if tech_analysis_results else None,
             macd_signal=tech_analysis_results.get('macd_signal') if tech_analysis_results else None,
             macd_hist=tech_analysis_results.get('macd_hist') if tech_analysis_results else None,
             sma_50=tech_analysis_results.get('sma_50') if tech_analysis_results else None,
             bb_upper=tech_analysis_results.get('bb_upper') if tech_analysis_results else None,
             bb_middle=tech_analysis_results.get('bb_middle') if tech_analysis_results else None,
             bb_lower=tech_analysis_results.get('bb_lower') if tech_analysis_results else None,
             confidence_score=tech_analysis_results.get('confidence', {}).get('overall_score') if tech_analysis_results else None,
             confidence_direction=tech_analysis_results.get('confidence', {}).get('direction') if tech_analysis_results else None,
             confidence_supporting=",".join(tech_analysis_results.get('confidence', {}).get('supporting_indicators', [])) if tech_analysis_results else None,
             confidence_conflicting=",".join(tech_analysis_results.get('confidence', {}).get('conflicting_indicators', [])) if tech_analysis_results else None,
            # Add Twitter sentiment data to report
            twitter_sentiment_summary=twitter_sentiment_results.get('summary', '')[:1000] if twitter_sentiment_results else None,
            twitter_sentiment_overall=twitter_sentiment_results.get('overall_sentiment') if twitter_sentiment_results else None
        )
        try:
            # Save report (consider if Twitter data should be included)
            await report_repository.create_report(db=db_session, report_data=report_to_save)
            print(f"Report saved for {actual_coin_id}")
        except Exception as db_err:
            print(f"Error saving report for {actual_coin_id}: {db_err}") # Log error but don't fail chat response

        return formatted_output, analysis_data

    except Exception as e:
        error_msg = f"An unexpected error occurred during analysis for '{coin_identifier}': {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg, None
    finally:
        await db_session.close()


def _format_currency_chat(value: float | None) -> str:
    """Formats currency for chat output."""
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


async def process_chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """
    Processes an incoming chat message, detects commands, and generates a response.

    Args:
        request: The incoming chat message request.

    Returns:
        The chatbot's response.
    """
    user_message = request.message.strip()
    session_id = request.session_id # Keep track for potential future use

    # 1. Check for Analyze Command
    match = ANALYZE_COMMAND_PATTERN.match(user_message)
    if match:
        coin_identifier = match.group(1)
        print(f"Detected analysis command for: {coin_identifier}")
        analysis_summary, analysis_data = await _run_analysis_for_chat(coin_identifier)

        if analysis_data: # Success
             return ChatMessageResponse(
                 response=f"Here's the analysis for {coin_identifier}:\n{analysis_summary}",
                 analysis_results=analysis_data,
                 session_id=session_id
             )
        else: # Error during analysis
             return ChatMessageResponse(
                 response=f"Sorry, I encountered an error trying to analyze {coin_identifier}. {analysis_summary}",
                 error=analysis_summary, # Put error message here
                 session_id=session_id
             )

    # 2. Check for Greetings
    greetings = ["hello", "hi", "hey", "yo"]
    if user_message.lower() in greetings:
        return ChatMessageResponse(
            response="Hello! I'm your crypto analysis assistant. How can I help? Try 'analyze [symbol/name]' (e.g., 'analyze BTC').",
            session_id=session_id
        )

    # 3. Check for Simple Price Queries (before general fallback)
    # Example: "price of bitcoin", "how is eth doing?", "btc price?"
    # This is a basic check and can be expanded
    price_query_pattern = re.compile(r"(?:price of|how is|what's the price of)\s+([a-zA-Z0-9\-]+)\??", re.IGNORECASE)
    symbol_price_query_pattern = re.compile(r"^([a-zA-Z]{1,10})\s+(?:price|data)\??$", re.IGNORECASE) # e.g., "BTC price?"

    price_match = price_query_pattern.search(user_message)
    symbol_match = symbol_price_query_pattern.match(user_message)

    coin_identifier_for_price = None
    if price_match:
        coin_identifier_for_price = price_match.group(1)
    elif symbol_match:
        coin_identifier_for_price = symbol_match.group(1)

    if coin_identifier_for_price:
        print(f"Detected potential price query for: {coin_identifier_for_price}")
        # Attempt to fetch data directly
        try:
            coin_id = coin_identifier_for_price
            # Resolve symbol if necessary (similar logic to _run_analysis_for_chat)
            if bool(re.match(r"^[a-zA-Z0-9]{1,10}$", coin_identifier_for_price)) and '-' not in coin_identifier_for_price:
                 resolved_id = await get_coin_id_from_symbol(coin_identifier_for_price)
                 if resolved_id:
                     coin_id = resolved_id
                 else:
                     # If symbol resolution fails, maybe let Deepseek handle it? Or return specific error?
                     print(f"Could not resolve symbol '{coin_identifier_for_price}' for price query.")
                     # Falling through to Deepseek might be better than a hard error here.

            if coin_id: # Proceed if we have an ID (original or resolved)
                coin_data = await get_coin_data_by_id(coin_id)
                if coin_data and coin_data.market_data:
                    md = coin_data.market_data
                    usd_price = md.current_price.get("usd")
                    change_24h = md.price_change_percentage_24h

                    response_text = f"Current data for {coin_data.name} ({coin_data.symbol.upper()}):\n"
                    response_text += f"- Price: ${_format_currency_chat(usd_price)}\n"
                    response_text += f"- 24h Change: {change_24h:.2f}%" if change_24h is not None else "N/A"

                    return ChatMessageResponse(
                        response=response_text,
                        session_id=session_id
                    )
                else:
                    print(f"Could not fetch CoinGecko data for ID '{coin_id}' for price query.")
                    # Fall through to Deepseek if data fetch fails

        except Exception as e:
            print(f"Error during price query fetch for '{coin_identifier_for_price}': {e}")
            # Fall through to Deepseek on error

    # 4. Fallback to DeepSeek Chat (if not analyze command or price query)
    print(f"Passing message to DeepSeek chat: '{user_message}'")
    try:
        # TODO: Implement history management if needed
        deepseek_response = await get_deepseek_chat_response(message=user_message)
        if deepseek_response:
            return ChatMessageResponse(
                response=deepseek_response,
                session_id=session_id
            )
        else:
            # Handle case where DeepSeek returns None (e.g., API error handled within the function)
            return ChatMessageResponse(
                response="Sorry, I couldn't get a response from the AI assistant at the moment.",
                error="DeepSeek chat returned no response.",
                session_id=session_id
            )
    except Exception as e:
        # Handle potential exceptions raised by get_deepseek_chat_response (like HTTPStatusError)
        print(f"Error calling DeepSeek chat service: {e}")
        return ChatMessageResponse(
            response="Sorry, there was an error connecting to the AI assistant.",
            error=str(e),
            session_id=session_id
        )
