import re

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Artifact base class."""

    artifact: str = Field(..., description="The value of the artifact")
    source_name: str = Field(..., description="The name of the source")
    reference_link: str = Field(
        default="", description="The reference link of the artifact"
    )
    reference_text: str = Field(
        default="", description="The reference text of the artifact"
    )

    def __init__(
        self,
        artifact: str,
        source_name: str,
        reference_link: str = "",
        reference_text: str = "",
    ):
        data = {
            "artifact": artifact,
            "source_name": source_name,
            "reference_link": reference_link,
            "reference_text": reference_text,
        }
        super().__init__(**data)

    def match(self, pattern: str) -> bool:
        """Return True if regex pattern matches the deobfuscated artifact, else False.

        May be overridden or extended by child classes.
        """
        regex = re.compile(pattern)
        return True if regex.search(self.__str__()) else False

    def format_message(self, message, **kwargs):
        """Allow string interpolation with artifact contents.

        Optionally extend in child classes to add support for more
        specific interpolations.

        Supported variables:

        * {artifact}
        * {reference_text}
        * {reference_link}
        """
        return message.format(
            artifact=str(self),
            reference_text=self.reference_text,
            reference_link=self.reference_link,
            **kwargs,
        )

    def _stringify(self) -> str:
        """Return str representation of the artifact.

        May be overridden in child classes.
        """
        return self.artifact

    def __str__(self) -> str:
        return self._stringify()
