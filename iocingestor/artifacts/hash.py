from typing import Dict, Optional

from iocingestor.artifacts.artifact import Artifact

# Types
MD5: str = "md5"
SHA1: str = "sha1"
SHA256: str = "sha256"
SHA512: str = "sha512"
HASH_MAP: Dict[int, str] = {32: MD5, 40: SHA1, 64: SHA256, 128: SHA512}


class Hash(Artifact):
    """Hash artifact abstraction."""

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {hash}
        * {hash_type}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(
            message, hash=str(self), hash_type=self.hash_type() or "hash"
        )

    def hash_type(self) -> Optional[str]:
        """Return the hash type as a string, or None."""
        return HASH_MAP.get(len(self.artifact))
