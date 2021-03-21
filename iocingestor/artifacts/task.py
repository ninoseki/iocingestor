from iocingestor.artifacts.artifact import Artifact


class Task(Artifact):
    """Generic Task artifact abstraction."""

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {task}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(message, task=str(self))
