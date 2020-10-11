from typing import Optional

from fastapi_utils.api_model import APIModel
from pydantic import Field


class Artifact(APIModel):
    artifact: str = Field(..., description="The value of the artifact")
    reference_link: str = Field(
        default="", description="The reference link of the artifact"
    )
    reference_text: str = Field(
        default="", description="The reference text of the artifact"
    )
    created_date: str = Field(..., description="The created datetime of the artifact")
    state: Optional[str] = Field(default=None, description="The state of the artifact")
