from hashlib import md5
from typing import List, Type
from urllib.parse import urlparse

from ioc_finder import (
    parse_domain_names,
    parse_ipv4_addresses,
    parse_ipv6_addresses,
    parse_md5s,
    parse_sha1s,
    parse_sha256s,
    parse_sha512s,
    parse_urls,
)
from ioc_finder.ioc_finder import _remove_items
from loguru import logger
from pydantic import BaseModel

from iocingestor.artifacts import URL, Artifact, Domain, Hash, IPAddress, Task
from iocingestor.ioc_fanger import fang

TRUNCATE_LENGTH = 280


class IoC(BaseModel):
    urls: List[str] = []
    domains: List[str] = []
    ips: List[str] = []
    hashes: List[str] = []

    @property
    def values(self) -> List[str]:
        return self.urls + self.domains + self.ips + self.hashes


class Source:
    """Base class for all Source plugins.

    Note: This is an abstract class. You must override ``__init__`` and ``run``
    in child classes. You should not override ``process_element``. When adding
    additional methods to child classes, consider prefixing the method name
    with an underscore to denote a ``_private_method``.
    """

    def __init__(self, name: str, *args, **kwargs):
        """Override this constructor in child classes.

        The first argument must always be ``name``.

        Other argumentss should be url, auth, etc, whatever is needed to set
        up the object.
        """
        raise NotImplementedError()

    def run(self, saved_state: str):
        """Run and return ``(saved_state, list(Artifact))``.

        Override this method in child classes.

        The method signature and return values must remain consistent.

        The method should attempt to pick up where we left off using
        ``saved_state``, if supported. If ``saved_state`` is ``None``, you can
        assume this is a first run. If state is maintained by the remote
        resource (e.g. as it is with SQS), ``saved_state`` should always be
        ``None``.
        """
        raise NotImplementedError()

    def _extract_iocs(self, content: str, strict=False) -> IoC:
        urls = parse_urls(content, False)
        if strict:
            urls_ = []
            for url in urls:
                if not url.startswith("http://") and not url.startswith("https://"):
                    urls_.append(url)
            # Remove obfuscated URLs (e.g. hxxp://google.co.jp)
            content = _remove_items(urls_, content)

        domains = parse_domain_names(content)
        ips = parse_ipv4_addresses(content) + parse_ipv6_addresses(content)
        hashes = (
            parse_md5s(content)
            + parse_sha1s(content)
            + parse_sha256s(content)
            + parse_sha512s(content)
        )
        return IoC(urls=urls, domains=domains, ips=ips, hashes=hashes)

    def nonobfuscated_iocs(self, content: str) -> IoC:
        return self._extract_iocs(content, strict=True)

    def all_iocs(self, content: str) -> IoC:
        return self._extract_iocs(fang(content))

    def obfuscated_iocs(self, content: str):
        nonobfuscated_iocs = self.nonobfuscated_iocs(content)
        memo = set(nonobfuscated_iocs.values)

        all_iocs = self.all_iocs(content)

        obfuscated_iocs = IoC(ips=all_iocs.ips, hashes=all_iocs.hashes)
        for url in all_iocs.urls:
            if url not in memo:
                obfuscated_iocs.urls.append(url)

        for domain in all_iocs.domains:
            if domain not in memo:
                obfuscated_iocs.domains.append(domain)

        return obfuscated_iocs

    def process_element(
        self, content: str, reference_link: str, include_nonobfuscated: bool = False
    ) -> List[Type[Artifact]]:
        """Take a single source content/url and return a list of Artifacts.

        This is the main work block of Source plugins, which handles
        IOC extraction and artifact creation.

        :param content: String content to extract from.
        :param reference_link: Reference link to attach to all artifacts.
        :param include_nonobfuscated: Include non-defanged URLs in output?
        """
        logger.debug(f"Processing in source '{self.name}'")

        # Truncate content to a reasonable length for reference_text.
        reference_text = content[:TRUNCATE_LENGTH] + (
            "..." if len(content) > TRUNCATE_LENGTH else ""
        )

        # Initialize an empty list and a map of counters to track each artifact type.
        artifact_list: List[Type[Artifact]] = []
        artifact_type_count = {
            "domain": 0,
            "hash": 0,
            "ipaddress": 0,
            "task": 0,
            "url": 0,
        }

        iocs = (
            self.all_iocs(content)
            if include_nonobfuscated
            else self.obfuscated_iocs(content)
        )

        for url in iocs.urls:
            artifact = URL(
                url,
                self.name,
                reference_link=reference_link,
                reference_text=reference_text,
            )

            # Dump URLs that appear to have the same domain as reference_url.
            try:
                if artifact.domain() == urlparse(reference_link).netloc:
                    continue
            except ValueError:
                # Error parsing reference_link as a URL. Ignoring.
                pass

            # Do URL collection.
            artifact_list.append(artifact)
            artifact_type_count["url"] += 1

        for domain in iocs.domains:
            artifact = Domain(
                domain,
                self.name,
                reference_link=reference_link,
                reference_text=reference_text,
            )

            # Dump domains that appear to have the same domain as reference_url.
            try:
                if str(artifact) == urlparse(reference_link).netloc:
                    continue
            except ValueError:
                # Error parsing reference_link as a URL. Ignoring.
                pass

            # Do URL collection.
            artifact_list.append(artifact)
            artifact_type_count["domain"] += 1

        for ip in iocs.ips:
            artifact = IPAddress(
                ip,
                self.name,
                reference_link=reference_link,
                reference_text=reference_text,
            )

            try:
                ipaddress = artifact.ipaddress()
                if (
                    ipaddress.is_private
                    or ipaddress.is_loopback
                    or ipaddress.is_reserved
                ):
                    # Skip private, loopback, reserved IPs.
                    continue

            except ValueError:
                # Skip invalid IPs.
                continue

            artifact_list.append(artifact)
            artifact_type_count["ipaddress"] += 1

        # Collect hashes.
        for hash_ in iocs.hashes:
            artifact = Hash(
                hash_,
                self.name,
                reference_link=reference_link,
                reference_text=reference_text,
            )

            artifact_list.append(artifact)
            artifact_type_count["hash"] += 1

        # Generate generic task.
        title = f"Manual Task: {reference_link}"
        description = f"URL: {reference_link}\nTask autogenerated by iocingestor from source: {self.name}"
        artifact = Task(
            title, self.name, reference_link=reference_link, reference_text=description
        )
        artifact_list.append(artifact)
        artifact_type_count["task"] += 1

        logger.debug(f"Found {len(artifact_list)} total artifacts")
        logger.debug(f"Type breakdown: {artifact_type_count}")
        return artifact_list

    def make_artifacts_unique(self, artifacts):
        memo = set()
        artifacts_ = []
        for artifact in artifacts:
            text = (
                artifact.artifact
                + artifact.source_name
                + artifact.reference_link
                + artifact.reference_text
            )
            key = md5(text.encode()).hexdigest()

            if key not in memo:
                artifacts_.append(artifact)

            memo.add(key)

        return artifacts_
