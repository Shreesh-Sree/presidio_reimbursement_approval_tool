from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.models.user import User
import httpx

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: str


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send message to AI assistant (employee-only feature)"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            response.raise_for_status()
            data = response.json()
            assistant_message = data["choices"][0]["message"]["content"]
            return ChatResponse(message=assistant_message)

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {exc.response.status_code}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message",
        ) from exc
