import iocextract

from iocingestor.artifacts.artifact import Artifact


class Domain(Artifact):
    """Domain artifact abstraction"""

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {domain}
        * {defanged}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(
            message, domain=str(self), defanged=iocextract.defang(str(self))
        )
