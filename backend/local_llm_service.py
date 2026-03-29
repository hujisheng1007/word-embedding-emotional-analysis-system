from fastapi import FastAPI

from app.schemas.llm_service import (
    ChatCompletionsChoice,
    ChatCompletionsRequest,
    ChatCompletionsResponse,
    ChatMessage,
)
from app.services.local_llm_runtime import LocalLLMRuntime

runtime = LocalLLMRuntime()
app = FastAPI(title="Campus Risk Local LLM Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": runtime.get_model_name(),
    }


@app.post("/v1/chat/completions", response_model=ChatCompletionsResponse)
def chat_completions(payload: ChatCompletionsRequest) -> ChatCompletionsResponse:
    result = runtime.generate_from_messages(
        [
            {"role": message.role, "content": message.content}
            for message in payload.messages
        ],
        max_new_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )
    return ChatCompletionsResponse(
        id=runtime.build_response_id(),
        object="chat.completion",
        choices=[
            ChatCompletionsChoice(
                index=0,
                message=ChatMessage(role="assistant", content=result.text),
                finish_reason=result.finish_reason,
            )
        ],
    )
