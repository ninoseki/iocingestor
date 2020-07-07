import csv
from typing import List, Optional, Type

from iocingestor.artifacts import URL, Artifact, Domain, Hash, IPAddress
from iocingestor.operators import Operator


class Plugin(Operator):
    """Operator for output to flat CSV file."""

    def __init__(
        self,
        filename: str,
        artifact_types: Optional[List[Type[Artifact]]] = None,
        filter_string: Optional[str] = None,
        allowed_sources: Optional[List[str]] = None,
    ):
        """CSV operator."""
        self.filename = filename

        super().__init__(artifact_types, filter_string, allowed_sources)
        self.artifact_types = artifact_types or [
            Domain,
            Hash,
            IPAddress,
            URL,
        ]

    def handle_artifact(self, artifact: Type[Artifact]):
        """Operate on a single artifact."""
        with open(self.filename, "a+", encoding="utf-8") as f:
            writer = csv.writer(f)
            artifact_type = artifact.__class__.__name__
            writer.writerow(
                [
                    artifact_type,
                    str(artifact),
                    artifact.reference_link,
                    artifact.reference_text,
                ]
            )
