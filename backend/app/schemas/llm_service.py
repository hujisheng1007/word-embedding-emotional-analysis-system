from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionsRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=96)


class ChatCompletionsChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionsResponse(BaseModel):
    id: str
    object: str
    choices: list[ChatCompletionsChoice]

