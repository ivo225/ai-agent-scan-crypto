import asyncio
import sys # Import sys for exit

# Try to import pandas, but handle the case where it's not installed
try:
    import pandas as pd
except ImportError:
    pd = None
# Import rich library
import rich.console
import rich.table
import rich.box

# Create console and define table class
Console = rich.console.Console
Table = rich.table.Table
box = rich.box
from typing import Dict, Optional, Any
import re # Import regex for symbol check
import traceback # Import traceback for detailed error printing

# Import Services
from app.services.coin_gecko_service import get_coin_data_by_id, get_coin_id_from_symbol, COINGECKO_API_BASE_URL
from app.services.crypto_panic_service import get_sentiment_data
from app.services.technical_analysis_service import get_technical_analysis
from app.services.deepseek_service import get_deepseek_analysis
from app.services.market_context_service import get_market_context # Import market context service
from app.services.perplexity_service import get_twitter_sentiment_for_coin # Import Twitter sentiment service
from app.utils.cache_manager import cache_manager # Import cache manager

# Import DB Components
from app.db.database import AsyncSessionLocal, init_db # Keep init_db import for potential direct use
from app.db.repositories import report_repository

# Import Models/Schemas
from app.models.coin import CoinData, CoinReportSchema # Import schema for saving
from app.models.report import CoinReport # Import model
from app.models.chat import ChatMessageRequest, ChatMessageResponse # Import chat models

# Import Chat Service
from app.services.chat_service import process_chat_message

# Initialize Rich console
console = Console()


# --- Helper Functions ---

def _format_currency(value: float | None, currency: str = "usd", precision: int = 2) -> str:
    """Formats a float as currency with specified precision."""
    if value is None:
        return "N/A"
    return f"${value:,.{precision}f}" # Use variable precision

def _display_analysis_results(
    coin_data: CoinData,
    tech_analysis: Optional[Dict[str, Optional[float]]],
    sentiment_data: Optional[Dict],
    deepseek_pred: Optional[str],
    market_context_data: Optional[Dict[str, Any]] = None, # Add market context arg
    twitter_sentiment: Optional[Dict[str, Any]] = None # Add Twitter sentiment arg
):
    """Displays combined analysis results in a formatted table."""
    table = Table(title=f"Analysis for {coin_data.name} ({coin_data.symbol.upper()})", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim", width=30)
    table.add_column("Value")

    # Basic Info
    table.add_row("CoinGecko ID", coin_data.id)
    table.add_row("Market Cap Rank", str(coin_data.market_cap_rank) if coin_data.market_cap_rank else "N/A")

    # Market Data
    md = coin_data.market_data
    usd = "usd"
    # Use higher precision for prices, standard for large volume/cap
    table.add_row("[bold]Current Price (USD)[/bold]", f"[bold cyan]{_format_currency(md.current_price.get(usd), usd, precision=6)}[/bold cyan]")
    table.add_row("Market Cap (USD)", _format_currency(md.market_cap.get(usd), usd, precision=2)) # Keep 2 for large numbers
    table.add_row("Total Volume (24h, USD)", _format_currency(md.total_volume.get(usd), usd, precision=2)) # Keep 2 for large numbers
    table.add_row("High (24h, USD)", f"[green]{_format_currency(md.high_24h.get(usd), usd, precision=6)}[/green]")
    table.add_row("Low (24h, USD)", f"[red]{_format_currency(md.low_24h.get(usd), usd, precision=6)}[/red]")

    # Format price change with color based on value
    if md.price_change_percentage_24h is not None:
        if md.price_change_percentage_24h > 0:
            price_change_str = f"[bold green]+{md.price_change_percentage_24h:.2f}%[/bold green]"
        elif md.price_change_percentage_24h < 0:
            price_change_str = f"[bold red]{md.price_change_percentage_24h:.2f}%[/bold red]"
        else:
            price_change_str = f"0.00%"
    else:
        price_change_str = "N/A"
    table.add_row("Price Change (24h)", price_change_str)

    # Supply
    table.add_row("Circulating Supply", f"{md.circulating_supply:,.0f}" if md.circulating_supply else "N/A")
    table.add_row("Total Supply", f"{md.total_supply:,.0f}" if md.total_supply else "N/A")
    table.add_row("Max Supply", f"{md.max_supply:,.0f}" if md.max_supply else "N/A")

    # Links
    homepage_list = coin_data.links.homepage
    website = homepage_list[0] if homepage_list else "N/A"
    table.add_row("Website", str(website))

    # Technical Analysis
    table.add_section()
    # Reverted: No longer checking for liquidity key
    table.add_row(f"[bold cyan]Technical Analysis (CoinGecko)[/bold cyan]", "")
    if tech_analysis:
        def fmt(key: str) -> str:
            val = tech_analysis.get(key)
            # Check if val is None or NaN
            if val is None or (pd and pd.isna(val)):
                return "N/A"

            # Format with colors based on indicator type
            if key == 'rsi':
                if val > 70: return f"[bold red]{val:.2f}[/bold red] (Overbought)"
                elif val < 30: return f"[bold green]{val:.2f}[/bold green] (Oversold)"
                else: return f"{val:.2f}"
            elif key in ['macd', 'macd_hist']:
                if val > 0: return f"[green]{val:.6f}[/green]"
                else: return f"[red]{val:.6f}[/red]"
            elif key.startswith('adx'):
                if key == 'adx':
                    if val > 30: return f"[bold]{val:.2f}[/bold] (Strong Trend)"
                    elif val > 20: return f"[bold]{val:.2f}[/bold] (Moderate Trend)"
                    else: return f"{val:.2f} (Weak Trend)"
                elif key == 'adx_plus_di' and val > tech_analysis.get('adx_minus_di', 0):
                    return f"[green]{val:.2f}[/green] (Bullish)"
                elif key == 'adx_minus_di' and val > tech_analysis.get('adx_plus_di', 0):
                    return f"[red]{val:.2f}[/red] (Bearish)"
                else:
                    return f"{val:.2f}"
            elif key.startswith('ema'):
                price = tech_analysis.get('current_price', None)
                if price is not None:
                    if price > val:
                        return f"[green]{val:.6f}[/green] (Price Above)"
                    else:
                        return f"[red]{val:.6f}[/red] (Price Below)"
                else:
                    return f"{val:.6f}"
            else:
                return f"{val:.6f}"

        # Momentum Indicators
        table.add_row("[bold]Momentum Indicators[/bold]", "")
        table.add_row("RSI (14)", fmt('rsi'))
        table.add_row("MACD (8, 17, 9)", fmt('macd'))
        table.add_row("MACD Signal (9)", fmt('macd_signal'))
        table.add_row("MACD Histogram", fmt('macd_hist'))

        # Trend Indicators
        table.add_row("[bold]Trend Indicators[/bold]", "")
        table.add_row("ADX (14)", fmt('adx'))
        table.add_row("DI+ (14)", fmt('adx_plus_di'))
        table.add_row("DI- (14)", fmt('adx_minus_di'))

        # Moving Averages
        table.add_row("[bold]Moving Averages[/bold]", "")
        table.add_row("SMA (50)", fmt('sma_50'))
        table.add_row("EMA (9)", fmt('ema_9'))
        table.add_row("EMA (21)", fmt('ema_21'))
        table.add_row("EMA (55)", fmt('ema_55'))

        # Volatility Indicators
        table.add_row("[bold]Volatility Indicators[/bold]", "")
        table.add_row("Bollinger Upper (20, 2)", fmt('bb_upper'))
        table.add_row("Bollinger Middle (20, 2)", fmt('bb_middle'))
        table.add_row("Bollinger Lower (20, 2)", fmt('bb_lower'))
    else:
        table.add_row("Indicators", "Failed/Skipped")

    # Sentiment
    table.add_section()
    table.add_row("[bold cyan]Sentiment (CryptoPanic)[/bold cyan]", "")
    table.add_row("Recent News Count", str(sentiment_data.get('count', 0)) if sentiment_data else "N/A")

    # Twitter Sentiment
    table.add_section()
    table.add_row("[bold cyan]Twitter Sentiment (Perplexity)[/bold cyan]", "")

    # Get the Twitter sentiment data from the function arguments
    if isinstance(deepseek_pred, str) and 'twitter_sentiment' in locals():
        # Use the twitter_sentiment parameter if available
        twitter_data = twitter_sentiment
    else:
        # Try to extract from deepseek_pred if it's a dict
        twitter_data = deepseek_pred.get('twitter_sentiment') if isinstance(deepseek_pred, dict) else None

    if twitter_data:
        overall = twitter_data.get('overall_sentiment', 'neutral').capitalize()
        table.add_row("Overall Sentiment", overall)
        key_tweets = twitter_data.get('key_tweets', [])
        if key_tweets:
            for i, tweet in enumerate(key_tweets[:3], 1):
                table.add_row(f"Key Tweet/Theme {i}", tweet[:100] + "..." if len(tweet) > 100 else tweet)
    else:
        table.add_row("Twitter Data", "Fetching in progress or unavailable")

    # Enhanced Market Context Display
    table.add_section()
    table.add_row("[bold cyan]Overall Market Context[/bold cyan]", "")
    if market_context_data:
        # Extract all market context components
        fear_greed = market_context_data.get('fear_greed')
        fear_greed_trend = market_context_data.get('fear_greed_trend')
        global_market = market_context_data.get('global_market')
        market_volatility = market_context_data.get('market_volatility')
        btc_dominance_data = market_context_data.get('btc_dominance')

        # Fear & Greed Index (Current)
        fg_value = fear_greed.get('value') if fear_greed else None
        fg_class = fear_greed.get('value_classification') if fear_greed else None

        # Format with color based on value
        if fg_value:
            fg_value_int = int(fg_value)
            if fg_value_int > 75:
                fg_display = f"[bold red]{fg_value} ({fg_class})[/bold red]"
            elif fg_value_int > 60:
                fg_display = f"[red]{fg_value} ({fg_class})[/red]"
            elif fg_value_int < 25:
                fg_display = f"[bold green]{fg_value} ({fg_class})[/bold green]"
            elif fg_value_int < 40:
                fg_display = f"[green]{fg_value} ({fg_class})[/green]"
            else:
                fg_display = f"[yellow]{fg_value} ({fg_class})[/yellow]"
        else:
            fg_display = "N/A"

        table.add_row("Fear & Greed Index", fg_display)

        # Fear & Greed Trend
        if fear_greed_trend:
            trend = fear_greed_trend.get('trend')
            trend_direction = fear_greed_trend.get('trend_direction')
            avg_value = fear_greed_trend.get('avg_value')

            # Format trend with color
            if trend in ['extreme_fear', 'fear']:
                trend_display = f"[green]{trend.replace('_', ' ').title()}[/green]"
            elif trend in ['extreme_greed', 'greed']:
                trend_display = f"[red]{trend.replace('_', ' ').title()}[/red]"
            else:
                trend_display = f"[yellow]{trend.replace('_', ' ').title()}[/yellow]"

            # Format direction with arrow
            if trend_direction == 'strongly_increasing':
                direction_display = "[bold green]↑↑[/bold green]"
            elif trend_direction == 'increasing':
                direction_display = "[green]↑[/green]"
            elif trend_direction == 'strongly_decreasing':
                direction_display = "[bold red]↓↓[/bold red]"
            elif trend_direction == 'decreasing':
                direction_display = "[red]↓[/red]"
            else:
                direction_display = "[yellow]→[/yellow]"

            table.add_row("F&G Trend (30d)", f"{trend_display} {direction_display} (avg: {avg_value})")

        # Global Market Data
        mkt_cap_change = global_market.get('market_cap_change_percentage_24h_usd') if global_market else None

        # Format with color based on value
        if mkt_cap_change is not None:
            if mkt_cap_change > 5.0:
                mkt_cap_display = f"[bold green]+{mkt_cap_change:.2f}%[/bold green] (Strong Uptrend)"
            elif mkt_cap_change > 2.0:
                mkt_cap_display = f"[green]+{mkt_cap_change:.2f}%[/green] (Uptrend)"
            elif mkt_cap_change < -5.0:
                mkt_cap_display = f"[bold red]{mkt_cap_change:.2f}%[/bold red] (Strong Downtrend)"
            elif mkt_cap_change < -2.0:
                mkt_cap_display = f"[red]{mkt_cap_change:.2f}%[/red] (Downtrend)"
            else:
                mkt_cap_display = f"[yellow]{mkt_cap_change:.2f}%[/yellow] (Stable)"
        else:
            mkt_cap_display = "N/A"

        table.add_row("Global Market Cap Change (24h)", mkt_cap_display)

        # Market Volatility
        if market_volatility:
            volatility_pattern = market_volatility.get('volatility_pattern')
            avg_volatility_24h = market_volatility.get('avg_volatility_24h')

            # Format with color based on volatility
            if volatility_pattern == 'highly_volatile':
                volatility_display = f"[bold red]{volatility_pattern.replace('_', ' ').title()}[/bold red] ({avg_volatility_24h:.2f}% 24h)"
            elif volatility_pattern == 'volatile':
                volatility_display = f"[red]{volatility_pattern.title()}[/red] ({avg_volatility_24h:.2f}% 24h)"
            elif volatility_pattern == 'moderate':
                volatility_display = f"[yellow]{volatility_pattern.title()}[/yellow] ({avg_volatility_24h:.2f}% 24h)"
            elif volatility_pattern == 'stable':
                volatility_display = f"[green]{volatility_pattern.title()}[/green] ({avg_volatility_24h:.2f}% 24h)"
            else:
                volatility_display = f"{volatility_pattern.title()} ({avg_volatility_24h:.2f}% 24h)"

            table.add_row("Market Volatility", volatility_display)

        # BTC Dominance
        if btc_dominance_data:
            btc_dominance = btc_dominance_data.get('btc_dominance')
            dominance_level = btc_dominance_data.get('dominance_level')
            market_implication = btc_dominance_data.get('market_implication')
            btc_eth_ratio = btc_dominance_data.get('btc_eth_ratio')

            # Format with color based on dominance level
            if dominance_level in ['very_high', 'high']:
                dominance_display = f"[bold red]{btc_dominance:.2f}%[/bold red] ({dominance_level.replace('_', ' ').title()})"
            elif dominance_level in ['very_low', 'low']:
                dominance_display = f"[bold green]{btc_dominance:.2f}%[/bold green] ({dominance_level.replace('_', ' ').title()})"
            else:
                dominance_display = f"[yellow]{btc_dominance:.2f}%[/yellow] ({dominance_level.replace('_', ' ').title()})"

            table.add_row("BTC Dominance", dominance_display)

            # Format market implication
            if market_implication == 'altcoin_bullish':
                implication_display = f"[green]{market_implication.replace('_', ' ').title()}[/green]"
            elif market_implication == 'altcoin_bearish':
                implication_display = f"[red]{market_implication.replace('_', ' ').title()}[/red]"
            else:
                implication_display = f"[yellow]{market_implication.replace('_', ' ').title()}[/yellow]"

            table.add_row("Market Implication", implication_display)
            table.add_row("BTC/ETH Ratio", f"{btc_eth_ratio:.2f}")
    else:
        table.add_row("Context Data", "Failed/Skipped")


    console.print(table)

    # DeepSeek Prediction
    console.print("\n[bold cyan]DeepSeek AI Analysis:[/bold cyan]")
    console.print(deepseek_pred if deepseek_pred else "[italic]No analysis generated or failed.[/italic]")

    # Add a small delay to ensure the DeepSeek analysis is fully displayed
    import time
    time.sleep(0.5)

    # AI Trading Signal and Confidence Assessment
    if tech_analysis and tech_analysis.get('confidence'):
        confidence = tech_analysis.get('confidence', {})
        score = confidence.get('overall_score')
        direction = confidence.get('direction', 'neutral').capitalize()
        signal = confidence.get('signal', 'HOLD')

        # Format score display
        if score is not None:
            if score >= 70: score_display = f"[bold green]{score}[/bold green]/100"
            elif score >= 40: score_display = f"[yellow]{score}[/yellow]/100"
            else: score_display = f"[red]{score}[/red]/100"
        else: score_display = "N/A"

        # Format signal display with more detailed information
        if signal == 'STRONG BUY':
            signal_display = f"[bold green]{signal}[/bold green]"
            signal_desc = "[green]Strongly bullish indicators suggest significant upside potential[/green]"
        elif signal == 'BUY':
            signal_display = f"[green]{signal}[/green]"
            signal_desc = "[green]Bullish indicators suggest upside potential[/green]"
        elif signal == 'STRONG SELL':
            signal_display = f"[bold red]{signal}[/bold red]"
            signal_desc = "[red]Strongly bearish indicators suggest significant downside risk[/red]"
        elif signal == 'SELL':
            signal_display = f"[red]{signal}[/red]"
            signal_desc = "[red]Bearish indicators suggest downside risk[/red]"
        else: # HOLD
            signal_display = f"[yellow]{signal}[/yellow]"
            signal_desc = "[yellow]Mixed or neutral indicators suggest waiting for clearer signals[/yellow]"

        # Create a prominent trading signal display with description
        console.print("\n[bold white on blue]╔══════════════════════════════════════════╗[/bold white on blue]")
        console.print(f"[bold white on blue]║      AI TRADING RECOMMENDATION       ║[/bold white on blue]")
        console.print(f"[bold white on blue]╠══════════════════════════════════════════╣[/bold white on blue]")
        console.print(f"[bold white on blue]║[/bold white on blue]            {signal_display}            [bold white on blue]║[/bold white on blue]")
        console.print(f"[bold white on blue]╠══════════════════════════════════════════╣[/bold white on blue]")
        console.print(f"[bold white on blue]║[/bold white on blue] {signal_desc} [bold white on blue]║[/bold white on blue]")
        console.print(f"[bold white on blue]╚══════════════════════════════════════════╝[/bold white on blue]")

        # Also add to the main table for completeness
        table.add_section()
        table.add_row("[bold]AI Trading Signal[/bold]", signal_display)

        # Add confidence details with enhanced display
        table.add_section()
        table.add_row("[bold cyan]Prediction Confidence[/bold cyan]", "")
        table.add_row("Overall Score", score_display)

        # Format direction with color
        if direction.lower() == 'bullish':
            direction_display = f"[green]{direction}[/green]"
        elif direction.lower() == 'bearish':
            direction_display = f"[red]{direction}[/red]"
        else:
            direction_display = f"[yellow]{direction}[/yellow]"
        table.add_row("Implied Direction", direction_display)

        # Format supporting and conflicting indicators
        supporting = confidence.get('supporting_indicators', [])
        if supporting:
            table.add_row("[green]Supporting Signals[/green]", ", ".join([f"[dim green]{s}[/dim green]" for s in supporting]))

        conflicting = confidence.get('conflicting_indicators', [])
        if conflicting:
            table.add_row("[red]Conflicting Signals[/red]", ", ".join([f"[dim red]{s}[/dim red]" for s in conflicting]))

        # Add agreement ratio if available
        agreement = confidence.get('indicator_agreement')
        if agreement is not None:
            if agreement > 0.7:
                agreement_display = f"[green]{agreement:.2f}[/green] (Strong)"
            elif agreement > 0.5:
                agreement_display = f"[yellow]{agreement:.2f}[/yellow] (Moderate)"
            else:
                agreement_display = f"[red]{agreement:.2f}[/red] (Weak)"
            table.add_row("Indicator Agreement", agreement_display)

def is_likely_symbol(input_str: str) -> bool:
    """Checks if the input string looks like a typical crypto symbol."""
    return bool(re.match(r"^[a-zA-Z0-9]{1,10}$", input_str)) and '-' not in input_str

# --- Core Analysis Logic ---

async def run_analysis(coin_identifier: str):
    """
    Performs a full analysis of a cryptocurrency and saves the report.
    Accepts either a CoinGecko ID or a Ticker Symbol.
    """
    console.print(f"Received identifier: [bold cyan]{coin_identifier}[/]")
    actual_coin_id = coin_identifier # Assume it's an ID initially
    is_symbol = is_likely_symbol(coin_identifier)

    if is_symbol:
        console.print(f"Identifier '{coin_identifier}' looks like a symbol. Attempting to find CoinGecko ID...")
        resolved_id = await get_coin_id_from_symbol(coin_identifier)
        if resolved_id:
            actual_coin_id = resolved_id
            console.print(f"Found ID: [bold green]{actual_coin_id}[/]. Proceeding with analysis.")
        else:
            console.print(f"[bold red]Error:[/bold red] Could not resolve symbol '{coin_identifier}' to a CoinGecko ID. Please use the full ID (e.g., 'bitcoin').")
            return # Stop if symbol resolution fails
    else:
         console.print(f"Identifier '{coin_identifier}' looks like a CoinGecko ID. Proceeding directly.")


    console.print(f"Starting analysis for [bold cyan]{actual_coin_id}[/]...")

    db_session = AsyncSessionLocal()
    tech_analysis_results = None
    sentiment_data_results = None
    deepseek_analysis_result = None
    coin_data_result = None
    market_context_data = None # Initialize market context

    try:
        # 1. Fetch Base Coin Data using the resolved/original ID
        console.print(f"Fetching base data from CoinGecko for ID: {actual_coin_id}...")
        coin_data_result = await get_coin_data_by_id(actual_coin_id)
        if not coin_data_result:
            console.print(f"[bold red]Error:[/bold red] Could not retrieve base data for '{actual_coin_id}'. Aborting analysis.")
            return

        # 2. Fetch Sentiment Data (still uses symbol from fetched data)
        console.print(f"Fetching sentiment data from CryptoPanic...")
        sentiment_data_results = await get_sentiment_data(coin_data_result.symbol) # Use symbol

        # 3. Perform Technical Analysis using the resolved/original ID
        console.print(f"Performing technical analysis for ID: {actual_coin_id} using up to 365 days...") # Updated message
        tech_analysis_results = await get_technical_analysis(actual_coin_id, days=365) # Changed days to 365
        if tech_analysis_results is None:
            console.print("[yellow]Warning:[/yellow] Technical analysis failed or returned no data.")
            # Proceed without TA data - tech_analysis_results remains None

        # 4. Fetch Market Context
        console.print(f"Fetching broader market context...")
        market_context_data = await get_market_context()

        # 5. Fetch Twitter Sentiment via Perplexity
        console.print(f"Fetching Twitter sentiment via Perplexity...")
        twitter_sentiment_results = await get_twitter_sentiment_for_coin(
            coin_name=coin_data_result.name,
            coin_symbol=coin_data_result.symbol
        )

        # 6. Get DeepSeek Analysis (Now passing all data including Twitter sentiment)
        console.print(f"Generating AI analysis via DeepSeek...")
        # Pass all data to the AI analysis function
        deepseek_analysis_result = await get_deepseek_analysis(
            coin_data=coin_data_result,
            sentiment_data=sentiment_data_results,
            technical_indicators=tech_analysis_results,
            market_context=market_context_data,
            twitter_sentiment=twitter_sentiment_results
        )

        # 7. Display Results with all data
        console.print("\n--- Analysis Complete ---")
        # Pass all data to display function
        _display_analysis_results(
            coin_data_result,
            tech_analysis_results,
            sentiment_data_results,
            deepseek_analysis_result,
            market_context_data, # Pass the context here
            twitter_sentiment_results # Pass Twitter sentiment data
        )

        # 7. Prepare and Save Report to DB (Silently)
        # Extract market context data safely
        fear_greed = market_context_data.get('fear_greed') if market_context_data else None
        global_market = market_context_data.get('global_market') if market_context_data else None
        btc_dom = None
        mkt_cap_change = None
        if global_market and isinstance(global_market.get('market_cap_percentage'), dict):
             btc_dom = global_market['market_cap_percentage'].get('btc')
        if global_market:
             mkt_cap_change = global_market.get('market_cap_change_percentage_24h_usd')


        report_to_save = CoinReportSchema(
            coin_id=coin_data_result.id,
            prediction=deepseek_analysis_result,
            entry_price_suggestion=None, # TODO
            sentiment_score=None, # TODO
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
            # Add market context fields
            fear_greed_value=int(fear_greed.get('value')) if fear_greed and fear_greed.get('value') else None,
            fear_greed_classification=fear_greed.get('value_classification') if fear_greed else None,
            market_cap_change_24h=mkt_cap_change,
            btc_dominance=btc_dom,
            # Add Twitter sentiment fields
            twitter_sentiment_summary=twitter_sentiment_results.get('summary', '')[:1000] if twitter_sentiment_results else None,
            twitter_sentiment_overall=twitter_sentiment_results.get('overall_sentiment') if twitter_sentiment_results else None
        )
        created_report = await report_repository.create_report(db=db_session, report_data=report_to_save)
        if created_report:
             console.print(f"[dim]Report saved with ID: {created_report.id}[/dim]") # Optional: Confirm save

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during the analysis process:[/bold red] {e}")
        traceback.print_exc() # Print full traceback for debugging
    finally:
        await db_session.close()


# --- Interactive Chat Loop ---

async def chat_loop():
    """Main interactive chat loop."""
    console.print("--- Crypto Analysis Chat ---", style="bold blue")
    console.print("Type '/analyze <symbol_or_id>' to analyze a coin.")
    console.print("Type '/exit' or '/quit' to leave.")

    while True:
        try:
            # Use asyncio.to_thread to run input() in a separate thread
            # This prevents blocking the asyncio event loop
            user_input = await asyncio.to_thread(input, "> ")
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "/quit"]:
                console.print("Exiting chat. Goodbye!", style="bold blue")
                break

            if user_input.lower().startswith("/analyze "):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2:
                    coin_identifier = parts[1].strip()
                    if coin_identifier:
                        await run_analysis(coin_identifier)
                    else:
                        console.print("[yellow]Usage:[/yellow] /analyze <symbol_or_id>")
                else:
                    console.print("[yellow]Usage:[/yellow] /analyze <symbol_or_id>")
            elif user_input.startswith("/"):
                 console.print(f"[yellow]Unknown command:[/yellow] {user_input.split()[0]}. Try '/analyze <id_or_symbol>' or '/exit'.")
            else:
                # Call the chat service to process the message
                # Using a placeholder session_id for CLI interaction
                request = ChatMessageRequest(message=user_input, session_id="cli_session")
                response: ChatMessageResponse = await process_chat_message(request)
                console.print(f"[green]Chat:[/green] {response.response}")
                if response.error:
                    console.print(f"[bold red]Error in chat processing:[/bold red] {response.error}")

        except KeyboardInterrupt:
            console.print("\nExiting chat. Goodbye!", style="bold blue")
            break
        except Exception as e:
            console.print(f"[bold red]An error occurred in the chat loop:[/bold red] {e}")
            traceback.print_exc() # Print full traceback for debugging


# --- Database Setup Command ---

async def setup_database():
    """Initialize the database schema."""
    console.print("Setting up database...", style="bold blue")
    try:
        await init_db()
        console.print("[bold green]Database setup complete![/bold green] Tables have been created/recreated.")
    except Exception as e:
        console.print(f"[bold red]Error setting up database:[/bold red] {e}")
        traceback.print_exc()

# --- Cache Management Commands ---

async def show_cache_stats():
    """Display statistics about the current cache."""
    stats = await cache_manager.get_stats()

    console.print("[bold cyan]Cache Statistics[/bold cyan]")
    console.print(f"Total namespaces: {stats['total_namespaces']}")
    console.print(f"Total entries: {stats['total_entries']}")

    # Display TTL settings
    ttl_table = Table(title="Default TTL Settings (seconds)")
    ttl_table.add_column("Namespace", style="cyan")
    ttl_table.add_column("TTL (seconds)", justify="right")

    for namespace, ttl in stats['default_ttls'].items():
        ttl_table.add_row(namespace, str(ttl))

    console.print(ttl_table)

    # Display namespace details
    if stats['namespaces']:
        ns_table = Table(title="Cache Namespaces")
        ns_table.add_column("Namespace", style="cyan")
        ns_table.add_column("Total Entries", justify="right")
        ns_table.add_column("Active", justify="right", style="green")
        ns_table.add_column("Expired", justify="right", style="yellow")

        for namespace, details in stats['namespaces'].items():
            ns_table.add_row(
                namespace,
                str(details['total_entries']),
                str(details['active_entries']),
                str(details['expired_entries'])
            )

        console.print(ns_table)
    else:
        console.print("[yellow]No cache entries found.[/yellow]")

async def clear_cache(namespace=None):
    """Clear the cache, optionally for a specific namespace only."""
    if namespace:
        count = await cache_manager.clear_namespace(namespace)
        console.print(f"[green]Cleared {count} entries from namespace '{namespace}'[/green]")
    else:
        count = await cache_manager.clear_all()
        console.print(f"[green]Cleared all caches ({count} total entries)[/green]")

async def set_cache_ttl(namespace, ttl_seconds):
    """Set the TTL for a specific namespace."""
    try:
        ttl = int(ttl_seconds)
        if ttl <= 0:
            console.print("[red]TTL must be a positive integer[/red]")
            return

        cache_manager.set_default_ttl(namespace, ttl)
        console.print(f"[green]Set TTL for namespace '{namespace}' to {ttl} seconds[/green]")
    except ValueError:
        console.print("[red]TTL must be a valid integer[/red]")

# --- Command Line Interface ---

async def main():
    """Main entry point for the CLI."""
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "setup-db":
            await setup_database()
            return
        elif command == "cache-stats":
            await show_cache_stats()
            return
        elif command == "cache-clear":
            if len(sys.argv) > 2:
                namespace = sys.argv[2]
                await clear_cache(namespace)
            else:
                await clear_cache()
            return
        elif command == "cache-ttl":
            if len(sys.argv) < 4:
                console.print("[red]Usage: cache-ttl <namespace> <seconds>[/red]")
            else:
                namespace = sys.argv[2]
                ttl_seconds = sys.argv[3]
                await set_cache_ttl(namespace, ttl_seconds)
            return
        elif command == "--help" or command == "-h":
            console.print("Available commands:", style="bold blue")
            console.print("  setup-db    - Initialize the database schema (warning: this will drop existing tables)")
            console.print("  cache-stats - Show cache statistics")
            console.print("  cache-clear - Clear all caches")
            console.print("  cache-clear <namespace> - Clear a specific cache namespace")
            console.print("  cache-ttl <namespace> <seconds> - Set TTL for a namespace")
            console.print("  --help, -h  - Show this help message")
            console.print("  (no args)   - Start the interactive chat interface")
            return

    # Default: run the chat loop
    await chat_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nExiting.", style="bold blue")
        sys.exit(0)
