"""
Chat and Message router — CRUD operations and SSE streaming.
"""

import json
import time
import asyncio
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, Chat, Message, Project
from app.security.dependencies import get_current_user
from app.schemas import (
    ChatCreateRequest,
    ChatUpdateRequest,
    ChatResponse,
    MessageCreateRequest,
    MessageResponse,
    MessageDetail,
)
from app.prompt_engine import (
    PromptBuilder,
    ProviderConfig,
    TaskType,
    get_provider,
)

router = APIRouter(tags=["Chats"])


# ── Chats ─────────────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/chats",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat",
)
async def create_chat(
    project_id: UUID,
    body: ChatCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ChatResponse:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    chat = Chat(
        id=uuid4(),
        project_id=project.id,
        title=body.title,
        model_id=body.model_id,
        folder_id=body.folder_id,
        agent_id=body.agent_id,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return ChatResponse.model_validate(chat)


@router.get(
    "/projects/{project_id}/chats",
    response_model=list[ChatResponse],
    summary="List chats in a project",
)
async def list_chats(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[ChatResponse]:
    chats = (
        db.query(Chat)
        .filter(Chat.project_id == project_id, Chat.is_archived == False)
        .order_by(Chat.updated_at.desc())
        .all()
    )
    return [ChatResponse.model_validate(c) for c in chats]


@router.get(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    summary="Get a specific chat",
)
async def get_chat(
    chat_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ChatResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return ChatResponse.model_validate(chat)


@router.patch(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    summary="Update a chat (rename, pin, archive, move to folder)",
)
async def update_chat(
    chat_id: UUID,
    body: ChatUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ChatResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chat, field, value)

    db.commit()
    db.refresh(chat)
    return ChatResponse.model_validate(chat)


@router.delete(
    "/chats/{chat_id}",
    response_model=MessageDetail,
    summary="Delete a chat and all its messages",
)
async def delete_chat(
    chat_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return MessageDetail(message="Chat deleted successfully")


@router.get(
    "/chats/{chat_id}/export",
    summary="Export chat as JSON",
)
async def export_chat(
    chat_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return {
        "chat": ChatResponse.model_validate(chat).model_dump(mode="json"),
        "messages": [MessageResponse.model_validate(m).model_dump(mode="json") for m in messages],
    }


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get(
    "/chats/{chat_id}/messages",
    response_model=list[MessageResponse],
    summary="List messages in a chat",
)
async def list_messages(
    chat_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[MessageResponse]:
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and get AI response",
)
async def send_message(
    chat_id: UUID,
    body: MessageCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    # Save user message
    user_msg = Message(
        id=uuid4(),
        chat_id=chat.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    db.commit()

    # Build prompt with the engine
    recent = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    recent_messages = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent)
    ]

    provider_config = ProviderConfig(
        provider_name="bedrock",
        model_id=chat.model_id,
    )

    compiled = (
        PromptBuilder(provider_config)
        .set_task(TaskType.GENERAL)
        .auto_select_modules()
        .set_conversation(None, recent_messages)
        .set_user_message(body.content)
        .compile()
    )

    # Get AI response
    provider = get_provider("bedrock")
    result = await provider.generate(compiled)

    # Save assistant message
    assistant_msg = Message(
        id=uuid4(),
        chat_id=chat.id,
        role="assistant",
        content=result["content"],
        prompt_tokens=result.get("prompt_tokens"),
        completion_tokens=result.get("completion_tokens"),
        total_tokens=result.get("total_tokens"),
        latency_ms=result.get("latency_ms"),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return MessageResponse.model_validate(assistant_msg)


@router.post(
    "/chats/{chat_id}/messages/stream",
    summary="Send a message and stream the AI response via SSE",
)
async def stream_message(
    chat_id: UUID,
    body: MessageCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> StreamingResponse:
    import traceback as tb

    start_time = time.perf_counter()
    auth_duration = time.perf_counter() - start_time

    # 1. Fetch Chat in threadpool
    chat_start = time.perf_counter()
    chat = await asyncio.to_thread(lambda: db.query(Chat).filter(Chat.id == chat_id).first())
    chat_fetch_duration = time.perf_counter() - chat_start
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    # 2. Save User Message and commit in threadpool
    user_save_start = time.perf_counter()
    user_msg = Message(
        id=uuid4(),
        chat_id=chat.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await asyncio.to_thread(db.commit)
    user_msg_save_duration = time.perf_counter() - user_save_start

    # 3. Build prompt and fetch history in threadpool
    try:
        history_start = time.perf_counter()
        recent = await asyncio.to_thread(
            lambda: db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(20)
            .all()
        )
        recent_messages = [
            {"role": m.role, "content": m.content}
            for m in reversed(recent)
        ]
        history_fetch_duration = time.perf_counter() - history_start

        compile_start = time.perf_counter()
        provider_config = ProviderConfig(
            provider_name="bedrock",
            model_id=chat.model_id,
        )

        compiled = (
            PromptBuilder(provider_config)
            .set_task(TaskType.GENERAL)
            .auto_select_modules()
            .set_conversation(None, recent_messages)
            .set_user_message(body.content)
            .enable_debug()
            .compile()
        )
        compile_duration = time.perf_counter() - compile_start

        provider = get_provider("bedrock")

    except Exception as e:
        error_detail = f"Prompt build failed: {type(e).__name__}: {e}\n{tb.format_exc()}"
        print(f"[STREAM_DEBUG] {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )

    async def event_generator():
        full_content = ""
        first_token_time = None
        stream_start_time = time.perf_counter()

        async for chunk in provider.stream(compiled):
            if first_token_time is None:
                first_token_time = time.perf_counter()
            # Parse chunk to accumulate content
            try:
                data_str = chunk.replace("data: ", "").strip()
                data = json.loads(data_str)
                if not data.get("done"):
                    full_content += data.get("content", "")
            except (json.JSONDecodeError, ValueError):
                pass
            yield chunk

        completion_end_time = time.perf_counter()
        ttft_duration = (first_token_time - stream_start_time) if first_token_time else 0.0
        generation_duration = completion_end_time - (first_token_time or stream_start_time)

        # Save assistant message after stream completes in threadpool
        save_db_start = time.perf_counter()
        assistant_msg = Message(
            id=uuid4(),
            chat_id=chat.id,
            role="assistant",
            content=full_content,
        )
        db.add(assistant_msg)
        await asyncio.to_thread(db.commit)
        db_save_duration = time.perf_counter() - save_db_start

        total_pipeline_time = time.perf_counter() - start_time

        # Print latency breakdown report in server logs
        print(
            f"\n=== LATENCY BREAKDOWN REPORT ===\n"
            f"Auth check: {auth_duration * 1000:.2f} ms\n"
            f"Chat fetch: {chat_fetch_duration * 1000:.2f} ms\n"
            f"User Msg Save: {user_msg_save_duration * 1000:.2f} ms\n"
            f"History Fetch: {history_fetch_duration * 1000:.2f} ms\n"
            f"Prompt Compile: {compile_duration * 1000:.2f} ms\n"
            f"LLM First Token (TTFT): {ttft_duration * 1000:.2f} ms\n"
            f"LLM Generation: {generation_duration * 1000:.2f} s\n"
            f"Assistant Msg Save: {db_save_duration * 1000:.2f} ms\n"
            f"Total Request Time: {total_pipeline_time * 1000:.2f} ms\n"
            f"================================\n"
        )

        # Yield timing metrics as the final SSE event packet
        metrics = {
            "metrics": {
                "auth_ms": round(auth_duration * 1000, 2),
                "chat_fetch_ms": round(chat_fetch_duration * 1000, 2),
                "user_msg_save_ms": round(user_msg_save_duration * 1000, 2),
                "history_fetch_ms": round(history_fetch_duration * 1000, 2),
                "compile_ms": round(compile_duration * 1000, 2),
                "ttft_ms": round(ttft_duration * 1000, 2),
                "generation_ms": round(generation_duration * 1000, 2),
                "db_save_ms": round(db_save_duration * 1000, 2),
                "total_ms": round(total_pipeline_time * 1000, 2),
            },
            "done": True,
            "content": ""
        }
        yield f"data: {json.dumps(metrics)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

