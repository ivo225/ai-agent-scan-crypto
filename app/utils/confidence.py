from typing import Dict, Optional, List, Tuple, Any, Literal # Import Any and Literal

# Define the trading signal type
TradingSignal = Literal['STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL']

def generate_trading_signal(confidence_score: int, direction: str, price: Optional[float],
                          tech_indicators: Dict[str, Optional[float]]) -> TradingSignal:
    """
    Generates a trading signal (STRONG BUY, BUY, HOLD, SELL, STRONG SELL) based on
    confidence score, direction, and technical indicators.

    Args:
        confidence_score: Overall confidence score (0-100)
        direction: Predicted direction ('bullish', 'bearish', or 'neutral')
        price: Current price of the asset (can be None)
        tech_indicators: Dictionary of technical indicator values

    Returns:
        A trading signal as a string
    """
    # Default to HOLD if we can't make a confident decision
    signal: TradingSignal = 'HOLD'

    # Get key indicators for additional signal refinement
    rsi = tech_indicators.get('rsi')
    adx = tech_indicators.get('adx')
    macd = tech_indicators.get('macd')
    macd_signal = tech_indicators.get('macd_signal')
    macd_hist = tech_indicators.get('macd_hist')
    ema_9 = tech_indicators.get('ema_9')
    ema_21 = tech_indicators.get('ema_21')
    ema_55 = tech_indicators.get('ema_55')
    plus_di = tech_indicators.get('adx_plus_di')
    minus_di = tech_indicators.get('adx_minus_di')

    # Count strong bullish/bearish signals to determine final signal
    bullish_signals = 0
    bearish_signals = 0

    # 1. Base signal on direction and confidence (lower thresholds for more varied signals)
    if direction == 'bullish':
        if confidence_score >= 60:  # Lowered from 70
            bullish_signals += 2  # Strong signal
        elif confidence_score >= 30:  # Lowered from 40
            bullish_signals += 1  # Moderate signal
    elif direction == 'bearish':
        if confidence_score >= 60:  # Lowered from 70
            bearish_signals += 2  # Strong signal
        elif confidence_score >= 30:  # Lowered from 40
            bearish_signals += 1  # Moderate signal

    # 2. RSI conditions
    if rsi is not None:
        if rsi <= 30:  # Oversold (increased from 20)
            bullish_signals += 1
        elif rsi <= 20:  # Extremely oversold
            bullish_signals += 2
        elif rsi >= 70:  # Overbought (decreased from 80)
            bearish_signals += 1
        elif rsi >= 80:  # Extremely overbought
            bearish_signals += 2

    # 3. MACD conditions
    if all(x is not None for x in [macd, macd_signal, macd_hist]):
        # MACD crossover (bullish when MACD crosses above signal)
        if macd > macd_signal:
            bullish_signals += 1
            # Extra point if histogram is positive and increasing
            if macd_hist > 0 and macd_hist > 0.1 * abs(macd):  # Significant positive histogram
                bullish_signals += 1
        # MACD crossover (bearish when MACD crosses below signal)
        elif macd < macd_signal:
            bearish_signals += 1
            # Extra point if histogram is negative and decreasing
            if macd_hist < 0 and abs(macd_hist) > 0.1 * abs(macd):  # Significant negative histogram
                bearish_signals += 1

        # If MACD and signal are very close, reduce the signal strength
        if abs(macd - macd_signal) < 0.05 * abs(macd) and macd != 0:
            if macd > macd_signal:
                bullish_signals -= 0.5  # Reduce bullish signal (MACD barely above signal)
            else:
                bearish_signals -= 0.5  # Reduce bearish signal (MACD barely below signal)

    # 4. EMA conditions
    if all(x is not None for x in [ema_9, ema_21, ema_55]):
        # Bullish EMA alignment
        if ema_9 > ema_21 > ema_55:
            bullish_signals += 2
        elif ema_9 > ema_21:  # Short-term bullish
            bullish_signals += 1
        # Bearish EMA alignment
        elif ema_9 < ema_21 < ema_55:
            bearish_signals += 2
        elif ema_9 < ema_21:  # Short-term bearish
            bearish_signals += 1

        # Price position relative to EMAs
        if price is not None:
            if price > ema_55:  # Price above long-term EMA
                bullish_signals += 1
            elif price < ema_55:  # Price below long-term EMA
                bearish_signals += 1

    # 5. ADX conditions
    if all(x is not None for x in [adx, plus_di, minus_di]):
        # Strong trend gives more weight to the direction
        if adx >= 25:  # Strong trend
            if plus_di > minus_di:  # Bullish trend
                bullish_signals += 1
                if adx >= 40:  # Very strong trend
                    bullish_signals += 1
            elif minus_di > plus_di:  # Bearish trend
                bearish_signals += 1
                if adx >= 40:  # Very strong trend
                    bearish_signals += 1

    # 6. Determine final signal based on bullish vs bearish signals
    signal_strength = bullish_signals - bearish_signals

    if signal_strength >= 6:  # Very strong bullish
        signal = 'STRONG BUY'
    elif signal_strength >= 3:  # Moderately bullish
        signal = 'BUY'
    elif signal_strength <= -7:  # Very strong bearish (increased threshold for STRONG SELL)
        signal = 'STRONG SELL'
    elif signal_strength <= -4:  # Moderately bearish (increased threshold for SELL)
        signal = 'SELL'
    elif signal_strength >= 1:  # Slightly bullish
        signal = 'HOLD'
        # Lean bullish but not enough for BUY
    elif signal_strength <= -1:  # Slightly bearish
        signal = 'HOLD'
        # Lean bearish but not enough for SELL
    else:  # Truly neutral (0)
        signal = 'HOLD'

    # 7. Special case: extremely oversold/overbought conditions
    if rsi is not None:
        # Extremely oversold but only override if not already STRONG SELL
        if rsi <= 20 and signal not in ['STRONG SELL', 'SELL']:
            # If ADX confirms with bullish trend, make it STRONG BUY
            if adx is not None and adx >= 25 and plus_di is not None and minus_di is not None and plus_di > minus_di:
                signal = 'STRONG BUY'
            # Otherwise just BUY on extreme oversold
            else:
                signal = 'BUY'

        # Extremely overbought but only override if not already STRONG BUY
        elif rsi >= 80 and signal not in ['STRONG BUY', 'BUY']:
            # If ADX confirms with bearish trend, make it STRONG SELL
            if adx is not None and adx >= 25 and plus_di is not None and minus_di is not None and minus_di > plus_di:
                signal = 'STRONG SELL'
            # Otherwise just SELL on extreme overbought
            else:
                signal = 'SELL'

    return signal

def calculate_confidence_score(
    tech_indicators: Dict[str, Optional[float]],
    price: Optional[float], # Allow price to be None
    market_context: Optional[Dict[str, Any]] = None # Add market context parameter
) -> Dict[str, any]:
    """
    Calculate a confidence score (0-100) for predictions based on technical indicators
    and adjusted by broader market context.

    Args:
        tech_indicators: Dictionary of technical indicator values.
        price: Current price of the asset. Can be None if unavailable.
        market_context: Optional dictionary containing 'global_market' and 'fear_greed' data.

    Returns:
        Dictionary containing:
        - overall_score: 0-100 confidence score.
        - direction: 'bullish', 'bearish', or 'neutral'.
        - factor_scores: Dictionary of individual factor confidence scores.
        - supporting_indicators: List of indicators supporting the predicted direction.
        - conflicting_indicators: List of indicators against the predicted direction.
        - indicator_agreement: Ratio of agreeing indicators to total directional indicators.
    """
    scores = {}
    supporting = []
    conflicting = []

    # Track indicator votes (bullish/bearish count)
    votes = {'bullish': 0, 'bearish': 0, 'neutral': 0}

    # 1. RSI Analysis (0-20 points)
    rsi = tech_indicators.get('rsi')
    if rsi is not None:
        if rsi < 30:  # Oversold
            scores['rsi'] = min(20, (30 - rsi) * 1.5)  # More oversold = higher confidence
            votes['bullish'] += 1
            supporting.append('RSI oversold (<30)')
        elif rsi > 70:  # Overbought
            scores['rsi'] = min(20, (rsi - 70) * 1.5)  # More overbought = higher confidence
            votes['bearish'] += 1
            supporting.append('RSI overbought (>70)')
        else:
            # Neutral zone - less confidence contribution from RSI itself
            scores['rsi'] = max(0, 10 - abs(50 - rsi) * 0.2) # Score higher closer to 50
            votes['neutral'] += 1
    else:
        scores['rsi'] = 0

    # 2. MACD Analysis (0-25 points)
    macd = tech_indicators.get('macd')
    macd_signal = tech_indicators.get('macd_signal')
    macd_hist = tech_indicators.get('macd_hist')

    if all(x is not None for x in [macd, macd_signal, macd_hist]):
        # Score based on histogram magnitude (stronger divergence/convergence)
        hist_score = min(15, abs(macd_hist) * 50) # Scaled based on typical histogram values

        # Score based on crossover proximity (recent crossover = higher confidence)
        # Smaller difference means closer to crossover
        cross_proximity_score = max(0, 10 - abs(macd - macd_signal) * 20) # Scaled

        scores['macd'] = hist_score + cross_proximity_score

        # Determine direction based on MACD line vs Signal line AND histogram sign
        if macd > macd_signal and macd_hist > 0:
            votes['bullish'] += 1
            supporting.append('MACD bullish crossover/positive hist')
        elif macd < macd_signal and macd_hist < 0:
            votes['bearish'] += 1
            supporting.append('MACD bearish crossover/negative hist')
        else: # Divergence or conflicting signals within MACD
             votes['neutral'] += 1 # Or could assign weak vote based on dominant signal
             # Add conflicting note if needed
             if macd > macd_signal and macd_hist < 0: conflicting.append("MACD line/hist divergence")
             if macd < macd_signal and macd_hist > 0: conflicting.append("MACD line/hist divergence")

    else:
        scores['macd'] = 0

    # 3. Bollinger Bands Analysis (0-25 points)
    bb_upper = tech_indicators.get('bb_upper')
    bb_middle = tech_indicators.get('bb_middle')
    bb_lower = tech_indicators.get('bb_lower')

    if all(x is not None for x in [bb_upper, bb_middle, bb_lower]) and price is not None:
        band_width = bb_upper - bb_lower
        if band_width > 1e-6: # Avoid division by zero if bands are identical
            position = (price - bb_lower) / band_width  # 0 = at lower band, 1 = at upper band

            # Score based on extremes (near bands = higher confidence for reversal)
            if position < 0.1:  # Very near lower band
                scores['bb'] = min(25, (0.1 - position) * 250) # Stronger score closer to edge
                votes['bullish'] += 1 # Potential reversal buy signal
                supporting.append('Price near lower Bollinger Band')
            elif position > 0.9:  # Very near upper band
                scores['bb'] = min(25, (position - 0.9) * 250) # Stronger score closer to edge
                votes['bearish'] += 1 # Potential reversal sell signal
                supporting.append('Price near upper Bollinger Band')
            else:
                # Score higher closer to middle band (less extreme)
                scores['bb'] = max(0, 10 - abs(0.5 - position) * 20)
                votes['neutral'] += 1
        else:
            scores['bb'] = 0 # Bands too narrow to be useful
    else:
        scores['bb'] = 0

    # 4. SMA Analysis (0-20 points)
    sma_50 = tech_indicators.get('sma_50')

    if sma_50 is not None and price is not None:
        # Calculate % difference from SMA
        perc_diff = abs(price - sma_50) / sma_50 * 100 if sma_50 != 0 else 0

        # Score higher for clear breaks, lower for price near SMA (indecision)
        # Max score if price is > 5% away, min score if price is exactly at SMA
        scores['sma'] = min(20, perc_diff * 4)

        # Determine direction
        if price > sma_50:
            votes['bullish'] += 1
            supporting.append('Price > SMA 50')
        elif price < sma_50:
            votes['bearish'] += 1
            supporting.append('Price < SMA 50')
        else:
            votes['neutral'] += 1
    else:
        scores['sma'] = 0

    # 5. ADX Analysis (0-20 points)
    adx = tech_indicators.get('adx')
    plus_di = tech_indicators.get('adx_plus_di')
    minus_di = tech_indicators.get('adx_minus_di')

    if all(x is not None for x in [adx, plus_di, minus_di]):
        # ADX strength score (0-15 points)
        # ADX < 20: weak trend, 20-40: moderate trend, > 40: strong trend
        if adx < 20:
            adx_strength = adx / 2  # 0-10 points (weak trend = lower confidence)
            trend_strength_desc = "Weak"
        elif adx < 30:
            adx_strength = 10 + (adx - 20) / 2  # 10-15 points (moderate trend)
            trend_strength_desc = "Moderate"
        else:
            adx_strength = 15  # Maximum 15 points for very strong trend
            trend_strength_desc = "Strong"

        # Determine trend direction based on DI+ vs DI-
        di_diff = abs(plus_di - minus_di)
        di_diff_pct = di_diff / ((plus_di + minus_di) / 2) * 100 if (plus_di + minus_di) > 0 else 0

        # Add points for clear directional movement (0-5 points)
        # The larger the difference between DI+ and DI-, the clearer the trend direction
        directional_clarity = min(5, di_diff_pct / 10)  # Cap at 5 points

        if plus_di > minus_di:
            votes['bullish'] += 1
            if di_diff_pct > 20:  # Very clear bullish trend
                votes['bullish'] += 1  # Extra vote for strong directional clarity
                supporting.append(f'Strong ADX bullish signal (DI+ > DI- by {di_diff_pct:.1f}%)')
            else:
                supporting.append(f'ADX bullish (DI+ > DI-)')

            if adx > 25:
                supporting.append(f'{trend_strength_desc} trend (ADX={adx:.1f})')

        elif minus_di > plus_di:
            votes['bearish'] += 1
            if di_diff_pct > 20:  # Very clear bearish trend
                votes['bearish'] += 1  # Extra vote for strong directional clarity
                supporting.append(f'Strong ADX bearish signal (DI- > DI+ by {di_diff_pct:.1f}%)')
            else:
                supporting.append(f'ADX bearish (DI- > DI+)')

            if adx > 25:
                supporting.append(f'{trend_strength_desc} trend (ADX={adx:.1f})')
        else:
            votes['neutral'] += 1
            supporting.append('No clear trend direction (DI+ ≈ DI-)')

        # Calculate final ADX score
        scores['adx'] = min(20, adx_strength + directional_clarity)  # Cap at 20 points
    else:
        scores['adx'] = 0

    # 6. EMA Analysis (0-20 points)
    # Check for EMA crossovers and price position relative to EMAs
    ema_9 = tech_indicators.get('ema_9')
    ema_21 = tech_indicators.get('ema_21')
    ema_55 = tech_indicators.get('ema_55')

    ema_score = 0
    if all(x is not None for x in [ema_9, ema_21, ema_55]) and price is not None:
        # EMA alignment score (0-10 points)
        # Bullish: EMA9 > EMA21 > EMA55
        # Bearish: EMA9 < EMA21 < EMA55
        if ema_9 > ema_21 > ema_55:  # Perfect bullish alignment
            ema_score += 10
            votes['bullish'] += 2  # Stronger vote for perfect alignment
            supporting.append('Strong bullish EMA alignment (9 > 21 > 55)')
        elif ema_9 < ema_21 < ema_55:  # Perfect bearish alignment
            ema_score += 10
            votes['bearish'] += 2  # Stronger vote for perfect alignment
            supporting.append('Strong bearish EMA alignment (9 < 21 < 55)')
        elif ema_9 > ema_21:  # Partial bullish (short-term)
            ema_score += 5
            votes['bullish'] += 1
            supporting.append('Short-term bullish (EMA9 > EMA21)')
        elif ema_9 < ema_21:  # Partial bearish (short-term)
            ema_score += 5
            votes['bearish'] += 1
            supporting.append('Short-term bearish (EMA9 < EMA21)')

        # Check for recent crossovers (0-5 points)
        # This would be more accurate with historical data, but we can approximate
        # by checking how close the EMAs are to each other
        ema_9_21_diff_pct = abs(ema_9 - ema_21) / ema_21 * 100 if ema_21 != 0 else 0
        if ema_9_21_diff_pct < 0.5:  # EMAs are very close, potential crossover
            ema_score += 5
            if ema_9 > ema_21:
                supporting.append('Recent/potential bullish EMA9/21 crossover')
                votes['bullish'] += 1
            else:
                supporting.append('Recent/potential bearish EMA9/21 crossover')
                votes['bearish'] += 1

        # Price position relative to EMAs (0-5 points)
        if price > ema_55:  # Price above long-term EMA
            ema_score += 5
            votes['bullish'] += 1
            supporting.append('Price above EMA55 (bullish)')
        elif price < ema_55:  # Price below long-term EMA
            ema_score += 5
            votes['bearish'] += 1
            supporting.append('Price below EMA55 (bearish)')

        # Check price position relative to all EMAs for stronger signals
        if price > ema_9 and price > ema_21 and price > ema_55:
            supporting.append('Price above all EMAs (strongly bullish)')
            votes['bullish'] += 1
        elif price < ema_9 and price < ema_21 and price < ema_55:
            supporting.append('Price below all EMAs (strongly bearish)')
            votes['bearish'] += 1

        scores['ema'] = min(20, ema_score)  # Cap at 20 points
    else:
        scores['ema'] = 0

    # 7. Data Quality Score (0-10 points)
    # Count how many indicators are available vs. expected
    expected_indicators = [
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'bb_upper', 'bb_middle', 'bb_lower', 'sma_50',
        'adx', 'adx_plus_di', 'adx_minus_di',
        'ema_9', 'ema_21', 'ema_55'
    ]
    available = sum(1 for k in expected_indicators if tech_indicators.get(k) is not None)
    expected = len(expected_indicators)
    data_quality = min(10, (available / expected) * 10) if expected > 0 else 0
    scores['data_quality'] = data_quality

    # Calculate overall direction based on votes
    if votes['bullish'] > votes['bearish']:
        direction = 'bullish'
    elif votes['bearish'] > votes['bullish']:
        direction = 'bearish'
    else:
        direction = 'neutral'

    # Refine supporting/conflicting lists based on final direction
    final_supporting = []
    final_conflicting = []
    for item in supporting:
        is_supporting = (direction == 'bullish' and 'bullish' in item or 'oversold' in item or '> SMA' in item or 'lower Bollinger' in item) or \
                        (direction == 'bearish' and 'bearish' in item or 'overbought' in item or '< SMA' in item or 'upper Bollinger' in item)
        if is_supporting or direction == 'neutral':
            final_supporting.append(item)
        else:
            final_conflicting.append(item)
    # Add any existing conflicts (like MACD divergence)
    final_conflicting.extend(conflicting)


    # Calculate agreement score - how many indicators agree vs disagree with the final direction
    agreeing_votes = votes[direction] if direction != 'neutral' else 0
    disagreeing_votes = votes['bearish'] if direction == 'bullish' else votes['bullish'] if direction == 'bearish' else 0
    total_directional_votes = agreeing_votes + disagreeing_votes

    if total_directional_votes > 0:
        agreement_ratio = agreeing_votes / total_directional_votes
    else: # If only neutral votes or no votes
        agreement_ratio = 0.5 # Default to neutral agreement

    agreement_score = agreement_ratio * 10 # Max 10 points for agreement

    # Final score calculation (weighted sum of components + agreement)
    # Weights can be adjusted based on perceived importance
    overall_score = (
        scores.get('rsi', 0) * 0.10 +          # RSI contribution (10%) - Reduced from 15%
        scores.get('macd', 0) * 0.10 +         # MACD contribution (10%) - Reduced from 15%
        scores.get('bb', 0) * 0.10 +           # Bollinger Bands contribution (10%)
        scores.get('sma', 0) * 0.10 +          # SMA contribution (10%)
        scores.get('adx', 0) * 0.15 +          # ADX contribution (15%) - Reduced from 20%
        scores.get('ema', 0) * 0.15 +          # EMA contribution (15%) - Reduced from 20%
        scores.get('market_context', 0) * 0.20 + # Market context contribution (20%) - NEW
        scores.get('data_quality', 0) * 0.10 + # Data quality contribution (10%)
        agreement_score * 1.0                  # Agreement contribution (added on top)
    )

    # --- Market Context Analysis ---
    # Calculate a separate market context score (0-20 points)
    market_score = 0
    context_notes = []
    context_adjustment = 0

    if market_context:
        try:
            fear_greed = market_context.get('fear_greed')
            global_market = market_context.get('global_market')

            # --- Fear & Greed Index Analysis (0-10 points) ---
            if fear_greed and fear_greed.get('value'):
                fg_value = int(fear_greed.get('value'))
                fg_class = fear_greed.get('value_classification', 'N/A')

                # More granular scoring based on F&G value
                if direction == 'bullish':
                    if fg_value > 75: # Extreme Greed vs Bullish signal
                        market_score += 0  # No points (conflict)
                        context_adjustment -= 10  # Increased from 5
                        context_notes.append(f"Extreme Greed ({fg_value}) conflicts with bullish signal")
                    elif fg_value > 60: # Greed vs Bullish signal
                        market_score += 2
                        context_adjustment -= 5
                        context_notes.append(f"Greed ({fg_value}) slightly conflicts with bullish signal")
                    elif fg_value < 25: # Extreme Fear vs Bullish signal (Contrarian)
                        market_score += 10  # Maximum points
                        context_adjustment += 10  # Increased from 5
                        context_notes.append(f"Extreme Fear ({fg_value}) strongly supports bullish signal (contrarian)")
                    elif fg_value < 40: # Fear vs Bullish signal (Contrarian)
                        market_score += 7
                        context_adjustment += 5
                        context_notes.append(f"Fear ({fg_value}) supports bullish signal (contrarian)")
                    else: # Neutral F&G
                        market_score += 5
                        context_notes.append(f"Neutral market sentiment ({fg_value})")

                elif direction == 'bearish':
                    if fg_value > 75: # Extreme Greed vs Bearish signal
                        market_score += 10  # Maximum points
                        context_adjustment += 10  # Increased from 5
                        context_notes.append(f"Extreme Greed ({fg_value}) strongly supports bearish signal")
                    elif fg_value > 60: # Greed vs Bearish signal
                        market_score += 7
                        context_adjustment += 5
                        context_notes.append(f"Greed ({fg_value}) supports bearish signal")
                    elif fg_value < 25: # Extreme Fear vs Bearish signal (Contrarian)
                        market_score += 0  # No points (conflict)
                        context_adjustment -= 10  # Increased from 5
                        context_notes.append(f"Extreme Fear ({fg_value}) conflicts with bearish signal (contrarian)")
                    elif fg_value < 40: # Fear vs Bearish signal (Contrarian)
                        market_score += 2
                        context_adjustment -= 5
                        context_notes.append(f"Fear ({fg_value}) slightly conflicts with bearish signal (contrarian)")
                    else: # Neutral F&G
                        market_score += 5
                        context_notes.append(f"Neutral market sentiment ({fg_value})")
                else: # Neutral direction
                    # For neutral direction, extreme sentiment in either direction is valuable information
                    if fg_value > 70 or fg_value < 30:
                        market_score += 5
                        context_notes.append(f"Extreme market sentiment ({fg_value}) with neutral technical signals")
                    else:
                        market_score += 3
                        context_notes.append(f"Neutral market sentiment ({fg_value}) aligns with neutral technical signals")

            # --- Market Trend Analysis (0-10 points) ---
            if global_market and global_market.get('market_cap_change_percentage_24h_usd') is not None:
                mkt_cap_change = global_market.get('market_cap_change_percentage_24h_usd')

                # More granular scoring based on market movement magnitude
                if direction == 'bullish':
                    if mkt_cap_change < -5.0: # Strong market down vs Bullish signal
                        market_score += 0  # No points (strong conflict)
                        context_adjustment -= 10  # Increased from 5
                        context_notes.append(f"Strong market down ({mkt_cap_change:.2f}%) conflicts with bullish signal")
                    elif mkt_cap_change < -2.0: # Moderate market down vs Bullish signal
                        market_score += 2
                        context_adjustment -= 5
                        context_notes.append(f"Market down ({mkt_cap_change:.2f}%) conflicts with bullish signal")
                    elif mkt_cap_change > 5.0: # Strong market up vs Bullish signal
                        market_score += 10  # Maximum points
                        context_adjustment += 10  # Increased from 5
                        context_notes.append(f"Strong market up ({mkt_cap_change:.2f}%) strongly supports bullish signal")
                    elif mkt_cap_change > 2.0: # Moderate market up vs Bullish signal
                        market_score += 7
                        context_adjustment += 5
                        context_notes.append(f"Market up ({mkt_cap_change:.2f}%) supports bullish signal")
                    else: # Neutral market
                        market_score += 5
                        context_notes.append(f"Stable market ({mkt_cap_change:.2f}%)")

                elif direction == 'bearish':
                    if mkt_cap_change < -5.0: # Strong market down vs Bearish signal
                        market_score += 10  # Maximum points
                        context_adjustment += 10  # Increased from 5
                        context_notes.append(f"Strong market down ({mkt_cap_change:.2f}%) strongly supports bearish signal")
                    elif mkt_cap_change < -2.0: # Moderate market down vs Bearish signal
                        market_score += 7
                        context_adjustment += 5
                        context_notes.append(f"Market down ({mkt_cap_change:.2f}%) supports bearish signal")
                    elif mkt_cap_change > 5.0: # Strong market up vs Bearish signal
                        market_score += 0  # No points (strong conflict)
                        context_adjustment -= 10  # Increased from 5
                        context_notes.append(f"Strong market up ({mkt_cap_change:.2f}%) conflicts with bearish signal")
                    elif mkt_cap_change > 2.0: # Moderate market up vs Bearish signal
                        market_score += 2
                        context_adjustment -= 5
                        context_notes.append(f"Market up ({mkt_cap_change:.2f}%) conflicts with bearish signal")
                    else: # Neutral market
                        market_score += 5
                        context_notes.append(f"Stable market ({mkt_cap_change:.2f}%)")
                else: # Neutral direction
                    # For neutral direction, extreme market moves are valuable information
                    if abs(mkt_cap_change) > 5.0:
                        market_score += 5
                        context_notes.append(f"Strong market movement ({mkt_cap_change:.2f}%) with neutral technical signals")
                    else:
                        market_score += 3
                        context_notes.append(f"Stable market ({mkt_cap_change:.2f}%) aligns with neutral technical signals")

            # --- BTC Dominance Analysis (0-5 points) ---
            if global_market and global_market.get('market_cap_percentage', {}).get('btc') is not None:
                btc_dominance = global_market.get('market_cap_percentage', {}).get('btc')

                # BTC dominance interpretation depends on the asset being analyzed
                # For simplicity, we'll use some general rules:
                # - Rising BTC dominance often negative for altcoins, positive for BTC
                # - Falling BTC dominance often positive for altcoins, can be negative for BTC

                # We'd need historical data to determine if dominance is rising/falling
                # For now, just use absolute levels as a general indicator
                if btc_dominance > 50: # High BTC dominance
                    context_notes.append(f"High BTC dominance ({btc_dominance:.2f}%)")
                    # This could be added to the adjustment logic with more context
                elif btc_dominance < 40: # Low BTC dominance
                    context_notes.append(f"Low BTC dominance ({btc_dominance:.2f}%)")
                    # This could be added to the adjustment logic with more context

            # Cap the market score at 20 points
            market_score = min(20, market_score)
            # Store the market score for inclusion in the weighted calculation
            scores['market_context'] = market_score
        except Exception as e:
            print(f"Error processing market context: {e}")
            # Continue without market context adjustment

    # Apply context adjustment and clamp score
    overall_score += context_adjustment
    overall_score = max(0, min(100, round(overall_score)))

    # Add context notes to supporting/conflicting lists
    for note in context_notes:
        if "supports" in note:
            final_supporting.append(f"Context: {note}")
        elif "conflicts" in note:
            final_conflicting.append(f"Context: {note}")


    # Generate trading signal based on confidence score and direction
    signal = generate_trading_signal(overall_score, direction, price, tech_indicators)

    # Return structured confidence data
    return {
        'overall_score': overall_score,
        'direction': direction,
        'signal': signal,  # Add the trading signal
        'factor_scores': scores, # For potential debugging/fine-tuning
        'supporting_indicators': list(set(final_supporting)) if 'final_supporting' in locals() else [], # Use set to remove duplicates
        'conflicting_indicators': list(set(final_conflicting)) if 'final_conflicting' in locals() else [],
        'indicator_agreement': round(agreement_ratio, 2) if 'agreement_ratio' in locals() else 0.5
    }
