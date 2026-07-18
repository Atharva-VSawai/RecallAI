from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    source_filter: str | None = Field(default=None, max_length=500)

    @field_validator("question", "source_filter")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class SlackIngestRequest(BaseModel):
    channel_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    limit: int = Field(default=100, ge=1, le=500)
