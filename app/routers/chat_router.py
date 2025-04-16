from fastapi import APIRouter, HTTPException, status
from app.models.chat import ChatMessageRequest, ChatMessageResponse
from app.services.chat_service import process_chat_message

router = APIRouter()

@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    summary="Send a message to the chatbot",
    description="Processes a user message, handles greetings, and triggers analysis commands like 'analyze BTC'.",
    tags=["Chat"]
)
async def handle_chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """
    Handles incoming chat messages.

    - Parses the message for commands (e.g., "analyze bitcoin").
    - If a command is detected, it triggers the corresponding action (e.g., crypto analysis).
    - Responds with greetings or analysis results.
    """
    try:
        response = await process_chat_message(request)
        return response
    except Exception as e:
        # Log the exception details here in a real application
        print(f"Error processing chat message: {e}")
        # Optionally include traceback
        # import traceback
        # traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while processing your message: {e}"
        )

# Optional: Add endpoint for chat history if needed later
# @router.get("/chat/history/{session_id}", ...)
# async def get_chat_history(...)
