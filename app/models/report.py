from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.db.database import Base

class CoinReport(Base):
    """
    SQLAlchemy model for storing coin analysis reports.
    """
    __tablename__ = "coin_reports"

    id = Column(Integer, primary_key=True, index=True)
    coin_id = Column(String, index=True, nullable=False, comment="CoinGecko ID (e.g., 'bitcoin')")
    prediction = Column(String, nullable=True, comment="Prediction text from DeepSeek")
    entry_price_suggestion = Column(Float, nullable=True, comment="Suggested entry price from DeepSeek")
    sentiment_score = Column(Float, nullable=True, comment="Aggregated sentiment score (e.g., from CryptoPanic)")
    # Add columns for Technical Analysis results
    rsi = Column(Float, nullable=True, comment="Relative Strength Index (RSI)")
    macd = Column(Float, nullable=True, comment="MACD line value (8, 17, 9)") # Updated comment
    macd_signal = Column(Float, nullable=True, comment="MACD signal line value (8, 17, 9)") # Updated comment
    macd_hist = Column(Float, nullable=True, comment="MACD histogram value (8, 17, 9)") # Updated comment
    # New indicators
    sma_50 = Column(Float, nullable=True, comment="50-day Simple Moving Average")
    # sma_200 = Column(Float, nullable=True, comment="200-day Simple Moving Average") # Removed
    bb_upper = Column(Float, nullable=True, comment="Bollinger Band Upper (20, 2)")
    bb_middle = Column(Float, nullable=True, comment="Bollinger Band Middle (20, 2)")
    bb_lower = Column(Float, nullable=True, comment="Bollinger Band Lower (20, 2)")
    # Confidence Score fields
    confidence_score = Column(Integer, nullable=True, comment="Overall confidence score (0-100)")
    confidence_direction = Column(String, nullable=True, comment="Predicted direction (bullish, bearish, neutral)")
    confidence_supporting = Column(String, nullable=True, comment="Comma-separated list of supporting indicators")
    confidence_conflicting = Column(String, nullable=True, comment="Comma-separated list of conflicting indicators")
    # Market Context Fields
    fear_greed_value = Column(Integer, nullable=True, comment="Fear & Greed Index value")
    fear_greed_classification = Column(String, nullable=True, comment="Fear & Greed Index classification")
    market_cap_change_24h = Column(Float, nullable=True, comment="Global market cap change % (24h)")
    btc_dominance = Column(Float, nullable=True, comment="Bitcoin dominance percentage")
    # Twitter Sentiment Fields
    twitter_sentiment_summary = Column(String, nullable=True, comment="Summary of Twitter sentiment from Perplexity")
    twitter_sentiment_overall = Column(String, nullable=True, comment="Overall Twitter sentiment (bullish, bearish, neutral)")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<CoinReport(id={self.id}, coin_id='{self.coin_id}', timestamp='{self.timestamp}')>"
