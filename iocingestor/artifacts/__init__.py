from iocingestor.artifacts.artifact import Artifact
from iocingestor.artifacts.domain import Domain
from iocingestor.artifacts.hash import MD5, SHA1, SHA256, SHA512, Hash
from iocingestor.artifacts.ip_address import IPAddress
from iocingestor.artifacts.task import Task
from iocingestor.artifacts.url import URL

# Define string mappings for artifact types.
# At the bottom because it uses the classes we just defined.
STRING_MAP = {
    "url": URL,
    "ipaddress": IPAddress,
    "domain": Domain,
    "hash": Hash,
    "task": Task,
}

__all__ = [
    "Artifact",
    "Domain",
    "Hash",
    "IPAddress",
    "Task",
    "URL",
    "STRING_MAP",
    "MD5",
    "SHA1",
    "SHA256",
    "SHA512",
]
