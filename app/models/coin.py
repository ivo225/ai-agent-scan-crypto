from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, List, Any

class MarketData(BaseModel):
    # Allow currency values to be None if not provided by API
    current_price: Dict[str, Optional[float]] = Field(..., description="Current price in different currencies")
    market_cap: Dict[str, Optional[float]] = Field(..., description="Market cap in different currencies")
    total_volume: Dict[str, Optional[float]] = Field(..., description="Total volume in different currencies")
    high_24h: Dict[str, Optional[float]] = Field(..., description="Highest price in the last 24 hours")
    low_24h: Dict[str, Optional[float]] = Field(..., description="Lowest price in the last 24 hours")
    # price_change_percentage_24h can also be None sometimes
    price_change_percentage_24h: Optional[float] = Field(None, description="Price change percentage in the last 24 hours")
    circulating_supply: Optional[float] = Field(None, description="Circulating supply")
    total_supply: Optional[float] = Field(None, description="Total supply")
    max_supply: Optional[float] = Field(None, description="Maximum supply")

class ReposUrl(BaseModel):
    github: Optional[List[HttpUrl]] = None
    bitbucket: Optional[List[HttpUrl]] = None

class Links(BaseModel):
    homepage: Optional[List[HttpUrl]] = None
    blockchain_site: Optional[List[HttpUrl]] = None
    official_forum_url: Optional[List[HttpUrl]] = None
    chat_url: Optional[List[HttpUrl]] = None
    announcement_url: Optional[List[HttpUrl]] = None
    twitter_screen_name: Optional[str] = None
    facebook_username: Optional[str] = None
    bitcointalk_thread_identifier: Optional[int] = None
    telegram_channel_identifier: Optional[str] = None
    subreddit_url: Optional[HttpUrl] = None
    repos_url: Optional[ReposUrl] = None # Use the nested model

class CoinData(BaseModel):
    id: str = Field(..., description="CoinGecko coin ID")
    symbol: str = Field(..., description="Coin symbol (ticker)")
    name: str = Field(..., description="Coin name")
    description: Dict[str, str] = Field(..., description="Coin description in different languages")
    links: Links = Field(..., description="Coin links (website, explorers, etc.)") # Use the nested Links model
    image: Dict[str, HttpUrl] = Field(..., description="Coin images (thumb, small, large)")
    market_cap_rank: Optional[int] = Field(None, description="Market cap rank")
    market_data: MarketData = Field(..., description="Market data")

    # Add model_config for Pydantic V2 if needed
    # model_config = ConfigDict(from_attributes=True)

class CoinSchema(BaseModel):
    """Schema for creating or updating coin data in the DB (if needed)."""
    id: str
    symbol: str
    name: str

    class Config:
        # orm_mode = True # Pydantic V1 compatibility, use from_attributes=True in V2
        from_attributes = True # For Pydantic V2

class CoinReportSchema(BaseModel):
    """Schema for the analysis report stored in the DB."""
    coin_id: str
    prediction: Optional[str] = None # Prediction text from DeepSeek
    entry_price_suggestion: Optional[float] = None # Suggested entry price from DeepSeek
    sentiment_score: Optional[float] = None # Aggregated sentiment score
    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    # New indicators
    sma_50: Optional[float] = None
    # sma_200: Optional[float] = None # Removed
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    # Confidence fields
    confidence_score: Optional[int] = None
    confidence_direction: Optional[str] = None
    confidence_supporting: Optional[str] = None # Stored as comma-separated string
    confidence_conflicting: Optional[str] = None # Stored as comma-separated string
    # Market Context Fields
    fear_greed_value: Optional[int] = None
    fear_greed_classification: Optional[str] = None
    market_cap_change_24h: Optional[float] = None
    btc_dominance: Optional[float] = None
    # Twitter Sentiment Fields
    twitter_sentiment_summary: Optional[str] = None
    twitter_sentiment_overall: Optional[str] = None
    # Let the database handle the default timestamp generation
    timestamp: Optional[datetime] = Field(None, description="Timestamp of report creation (set by DB)")

    class Config:
        # orm_mode = True # Pydantic V1
        from_attributes = True # For Pydantic V2
