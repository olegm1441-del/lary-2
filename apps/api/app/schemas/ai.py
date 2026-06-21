from pydantic import BaseModel, Field


class AiTestRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Краткое описание идеи проекта")


class AiTestResponse(BaseModel):
    provider: str
    module: str
    result: str
