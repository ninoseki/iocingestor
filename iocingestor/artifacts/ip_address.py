import ipaddress

import iocextract

from iocingestor.artifacts.artifact import Artifact


class IPAddress(Artifact):
    """IP address artifact abstraction.

    Use version and ipaddress() for processing.
    """

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {ipaddress}
        * {defanged}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(
            message, ipaddress=str(self), defanged=iocextract.defang(str(self))
        )

    def _stringify(self):
        """Always returns deobfuscated IP."""
        return (
            self.artifact.replace("[", "")
            .replace("]", "")
            .split("/")[0]
            .split(":")[0]
            .split(" ")[0]
        )

    @property
    def version(self):
        """Returns 4, 6, or None."""
        try:
            return ipaddress.IPv4Address(self._stringify()).version
        except ValueError:
            try:
                return ipaddress.IPv6Address(self._stringify()).version
            except ValueError:
                return None

    def ipaddress(self):
        """Return ipaddress.IPv4Address or ipaddress.IPv6Address object, or raise ValueError."""
        version = self.version
        if version == 4:
            return ipaddress.IPv4Address(self._stringify())
        if version == 6:
            return ipaddress.IPv6Address(self._stringify())

        raise ValueError(f"Invalid IP address '{self.artifact}'")
