"""Chat API endpoints with SSE streaming support."""

import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ConversationResponse,
    ConversationWithMessages,
    MentionRef,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_llm_service(db: Session = Depends(get_db)) -> LLMService:
    """Dependency to get LLM service instance."""
    return LLMService(db)


# ============== Chat Endpoints ==============

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    Send a message and get a non-streaming response.
    """
    try:
        response, conversation_id, message_id = await llm_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            project_id=request.project_id,
            mentions=request.mentions,
            provider_name=request.provider,
        )

        if response.error:
            raise HTTPException(status_code=500, detail=response.error)

        return ChatResponse(
            message=response.content,
            conversation_id=conversation_id,
            message_id=message_id,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    Send a message and get a streaming SSE response.
    """
    async def generate():
        try:
            async for chunk, conversation_id, message_id in llm_service.stream_chat(
                message=request.message,
                conversation_id=request.conversation_id,
                project_id=request.project_id,
                mentions=request.mentions,
                provider_name=request.provider,
            ):
                data = {
                    "type": "content",
                    "content": chunk,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                }
                yield f"data: {json.dumps(data)}\n\n"

            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except ValueError as e:
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============== Conversation Endpoints ==============

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    llm_service: LLMService = Depends(get_llm_service),
):
    """List recent conversations."""
    conversations = llm_service.list_conversations(project_id=project_id, limit=limit)

    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages),
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Get a conversation with all its messages."""
    conversation = llm_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = llm_service.get_conversation_messages(conversation_id)

    return ConversationWithMessages(
        id=conversation.id,
        title=conversation.title,
        project_id=conversation.project_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages),
        messages=[ChatMessageResponse.from_orm(msg) for msg in messages],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Delete a conversation."""
    if not llm_service.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


# ============== Mentionable Items Endpoints ==============

@router.get("/mentionables")
async def get_mentionable_items(
    project_id: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get items that can be mentioned with @ in chat.
    Returns datasets, files, and scripts.
    """
    from app.models.dataset import Dataset, DatasetFile
    from app.models.script import Script

    result = {
        "datasets": [],
        "files": [],
        "scripts": [],
    }

    # Query datasets
    dataset_query = db.query(Dataset)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    if query:
        dataset_query = dataset_query.filter(Dataset.name.ilike(f"%{query}%"))

    datasets = dataset_query.limit(20).all()

    for ds in datasets:
        path = f"@{ds.name}"
        if ds.study_name:
            path = f"@{ds.study_name}/{ds.name}"

        result["datasets"].append({
            "type": "dataset",
            "id": ds.id,
            "name": ds.name,
            "path": path,
            "study_name": ds.study_name,
            "version_name": ds.version_name,
            "row_count": ds.row_count,
            "column_count": ds.column_count,
        })

        # Also add individual files
        for file in ds.files:
            file_path = f"{path}/{file.file_name}"
            result["files"].append({
                "type": "file",
                "id": f"{ds.id}:{file.id}",
                "name": file.file_name,
                "path": file_path,
                "dataset_id": ds.id,
                "dataset_name": ds.name,
                "row_count": file.row_count,
                "column_count": file.column_count,
                "file_type": file.file_type,
            })

    # Query scripts
    script_query = db.query(Script)
    if query:
        script_query = script_query.filter(
            (Script.name.ilike(f"%{query}%")) |
            (Script.display_name.ilike(f"%{query}%"))
        )

    scripts = script_query.limit(20).all()

    for script in scripts:
        result["scripts"].append({
            "type": "script",
            "id": script.id,
            "name": script.name,
            "path": f"@scripts/{script.name}",
            "display_name": script.display_name,
            "description": script.description,
            "language": script.language,
        })

    return result
