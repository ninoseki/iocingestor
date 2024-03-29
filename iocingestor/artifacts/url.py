import ipaddress
from urllib.parse import urlparse

import iocextract

from iocingestor.artifacts.artifact import Artifact


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
