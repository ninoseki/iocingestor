import ipaddress
import re
from typing import Dict, Optional
from urllib.parse import urlparse

import iocextract
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


class URL(Artifact):
    """URL artifact abstraction, unicode-safe."""

    def _match_expression(self, pattern: str):
        """Process pattern as a condition expression.

        Raises ValueError if not a valid expression, else returns the
        truthiness of the expression.
        """
        NOT = "not "
        conditions = [c.strip().lower() for c in pattern.split(",")]
        for condition in conditions:
            if condition.lstrip(NOT) not in URL.__dict__:
                raise ValueError("not a condition expression")

            result = URL.__dict__[condition.lstrip(NOT)](self)
            if condition.startswith(NOT) and result:
                return False
            if not condition.startswith(NOT) and not result:
                return False

        return True

    def match(self, pattern: str):
        """Filter on some predefined conditions or a regex pattern.

        If pattern can be parsed as one of the conditions below, it returns the
        truthiness of the resulting expression; otherwise it is treated as regex.

        Valid conditions:

        * is_obfuscated
        * is_ipv4
        * is_ipv6
        * is_ip
        * is_domain
        * not {any above condition}
        * {any comma-separated list of above conditions}

        For example:

        * is_obfuscated, not is_ip
        * not is_obfuscated, is_domain
        """
        try:
            return self._match_expression(pattern)
        except ValueError:
            # not a valid condition expression, treat as regex instead
            return super().match(pattern)

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {url}
        * {defanged}
        * {domain}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(
            message,
            url=str(self),
            domain=self.domain(),
            defanged=iocextract.defang(str(self)),
        )

    def _stringify(self):
        """Always returns deobfuscated URL."""
        return iocextract.refang_url(self.artifact)

    def is_obfuscated(self):
        """Boolean: is an obfuscated URL?"""
        stringlike = self._stringify()
        if stringlike != self.artifact:
            # don't treat "example.com" as obfuscated
            if stringlike != "http://" + self.artifact:
                return True
        return False

    def is_ipv4(self):
        """Boolean: URL network location is an IPv4 address, not a domain?"""
        parsed = urlparse(iocextract.refang_url(self.artifact))

        try:
            ipaddress.IPv4Address(
                parsed.netloc.split(":")[0]
                .replace("[", "")
                .replace("]", "")
                .replace(",", ".")
            )
        except ValueError:
            return False

        return True

    def is_ipv6(self):
        """Boolean: URL network location is an IPv6 address, not a domain?"""
        # fix urlparse exception
        parsed = urlparse(iocextract.refang_url(self.artifact))

        # Handle RFC 2732 IPv6 URLs with and without port, as well as non-RFC IPv6 URLs
        if "]:" in parsed.netloc:
            ipv6 = ":".join(parsed.netloc.split(":")[:-1])
        else:
            ipv6 = parsed.netloc

        try:
            ipaddress.IPv6Address(ipv6.replace("[", "").replace("]", ""))
        except ValueError:
            return False

        return True

    def is_ip(self):
        """Boolean: URL network location is an IP address, not a domain?"""
        return self.is_ipv4() or self.is_ipv6()

    def domain(self):
        """Deobfuscated domain; undefined behavior if self.is_ip()."""
        return urlparse(self._stringify()).netloc.split(":")[0]

    def is_domain(self):
        """Boolean: URL network location might be a valid domain?"""
        try:
            # can't have non-ascii
            self.domain().encode("ascii")
        except UnicodeEncodeError:
            return False
        return (
            not self.is_ip()
            and len(self.domain()) > 3
            and "." in self.domain()[1:-1]
            and all([x.isalnum() or x in "-." for x in self.domain()])
            and self.domain()[self.domain().rfind(".") + 1 :].isalpha()
            and len(self.domain()[self.domain().rfind(".") + 1 :]) > 1
        )

    def deobfuscated(self):
        """Named method for clarity, same as str(my_url_object)."""
        return self.__str__()


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


class Task(Artifact):
    """Generic Task artifact abstraction."""

    def format_message(self, message: str, **kwargs):
        """Allow string interpolation with artifact contents.

        Supported variables:

        * {task}
        * All supported variables from Artifact.format_message
        """
        return super().format_message(message, task=str(self))


# Define string mappings for artifact types.
# At the bottom because it uses the classes we just defined.
STRING_MAP = {
    "url": URL,
    "ipaddress": IPAddress,
    "domain": Domain,
    "hash": Hash,
    "task": Task,
}
