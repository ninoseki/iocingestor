from typing import List, Optional, Type

from iocingestor.artifacts import URL, Artifact
from iocingestor.operators import Operator


class AbstractPlugin(Operator):
    """Operator for Abstract JSON"""

    def __init__(
        self,
        artifact_types: Optional[List[Type[Artifact]]] = None,
        filter_string: Optional[str] = None,
        allowed_sources: Optional[List[str]] = None,
        **kwargs
    ):
        # kwargs are used to dynamically form message body
        self.kwargs = kwargs

        super().__init__(
            artifact_types=artifact_types,
            filter_string=filter_string,
            allowed_sources=allowed_sources,
        )

        self.artifact_types = artifact_types or [URL]

    def handle_artifact(self, artifact: Type[Artifact]):
        """Operate on a single artifact"""
        message_body = {k: artifact.format_message(v) for (k, v) in self.kwargs.items()}
        self._put(message_body)

    def _put(self, content: str):
        raise NotImplementedError()
