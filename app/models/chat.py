from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatMessageRequest(BaseModel):
    """
    Represents a user's message sent to the chat endpoint.
    """
    message: str
    session_id: Optional[str] = None # Optional: For future session management

class ChatMessageResponse(BaseModel):
    """
    Represents the chatbot's response to a user's message.
    """
    response: str
    analysis_results: Optional[Dict[str, Any]] = None # To hold structured analysis data if applicable
    session_id: Optional[str] = None # Optional: For future session management
    error: Optional[str] = None # To indicate if an error occurred
