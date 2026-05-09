from typing import Literal

from pydantic import BaseModel, field_validator

ACCEPTED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


class DiagramUploadRequest(BaseModel):
    file_name: str
    content_type: str

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        if value not in ACCEPTED_CONTENT_TYPES:
            raise ValueError(
                f"content_type must be one of {sorted(ACCEPTED_CONTENT_TYPES)}, got '{value}'"
            )
        return value
