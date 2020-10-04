from typing import List, Optional, Type, Union, cast

import pymisp
from pymisp import MISPAttribute, MISPEvent

from iocingestor.artifacts import (
    MD5,
    SHA1,
    SHA256,
    URL,
    Artifact,
    Domain,
    Hash,
    IPAddress,
)
from iocingestor.operators import Operator


class Plugin(Operator):
    """Operator for MISP."""

    def __init__(
        self,
        url: str,
        key: str,
        ssl: bool = True,
        tags: Optional[List[str]] = None,
        artifact_types: Optional[List[Type[Artifact]]] = None,
        filter_string: Optional[str] = None,
        allowed_sources: Optional[List[str]] = None,
        include_artifact_source_name: bool = True,
        include_event_id_in_info: bool = False,
    ):
        """MISP operator."""
        self.api = pymisp.ExpandedPyMISP(url, key, ssl)
        if tags:
            self.tags = tags
        else:
            self.tags = ["type:OSINT"]
        self.event_info = "{source_name}"
        self.url = url

        super().__init__(artifact_types, filter_string, allowed_sources)
        self.artifact_types = artifact_types or [Domain, Hash, IPAddress, URL]

        self.include_artifact_source_name = include_artifact_source_name
        self.include_event_id_in_info = include_event_id_in_info

    def handle_artifact(self, artifact) -> MISPEvent:
        """Operate on a single artifact."""
        event = self._find_or_create_event(artifact)

        if isinstance(artifact, Domain):
            event = self.handle_domain(event, artifact)
        if isinstance(artifact, Hash):
            event = self.handle_hash(event, artifact)
        elif isinstance(artifact, IPAddress):
            event = self.handle_ipaddress(event, artifact)
        if isinstance(artifact, URL):
            event = self.handle_url(event, artifact)

        return self._update_or_create_event(event)

    def _update_event_info(self, event: MISPEvent) -> MISPEvent:
        """Update info of an event"""
        if str(event.id) in event.info:
            return event

        # Add an ID of an envet as a reference
        event.info = f"{event.info},{event.id}"
        return cast(MISPEvent, self.api.update_event(event))

    def _update_or_create_event(self, event: MISPEvent) -> MISPEvent:
        """Update or create an event for the artifact."""
        event_dict = event.to_dict()
        attributes = event_dict.get("Attribute", [])
        if len(attributes) == 0:
            return event

        if event_dict.get("id") is None:
            event = cast(MISPEvent, self.api.add_event(event, pythonify=True))
        else:
            event = cast(MISPEvent, self.api.update_event(event, pythonify=True))

        if self.include_event_id_in_info:
            return self._update_event_info(event)

        return event

    def _find_or_create_event(self, artifact: Type[Artifact]) -> MISPEvent:
        """Find or create an event for the artifact."""
        event = self._find_event(artifact)
        if event is not None:
            return event

        return self._create_event(artifact)

    def _find_event(self, artifact: Type[Artifact]) -> Optional[MISPEvent]:
        """Find an event which has the same refetrence link, return an Event object."""
        events = cast(
            List[Union[MISPEvent, MISPAttribute]],
            self.api.search(
                "events",
                limit=1,
                type_attribute="link",
                value=artifact.reference_link,
                pythonify=True,
            ),
        )
        events_ = cast(List[MISPEvent], events)
        if len(events_) == 1:
            return events_[0]

        return None

    def _create_event(self, artifact: Type[Artifact]) -> MISPEvent:
        """Create an event in MISP, return an Event object."""
        event = MISPEvent()
        event.info = self.event_info.format(source_name=artifact.source_name)

        # Add tags.
        for tag in self.tags:
            event.add_tag(tag)

        # Add references.
        if artifact.reference_link != "":
            event.add_attribute("link", artifact.reference_link)
        if artifact.reference_text != "":
            event.add_attribute("text", artifact.reference_text)
        if artifact.source_name != "" and self.include_artifact_source_name:
            event.add_attribute("other", f"source:{artifact.source_name}")

        return event

    def handle_domain(self, event: MISPEvent, domain: Domain) -> MISPEvent:
        """Handle a single domain."""
        event.add_attribute("domain", str(domain))
        return event

    def handle_hash(self, event: MISPEvent, hash_: Hash) -> MISPEvent:
        """Handle a single hash."""
        if hash_.hash_type() == MD5:
            event.add_attribute("md5", str(hash_))
        elif hash_.hash_type() == SHA1:
            event.add_attribute("sha1", str(hash_))
        elif hash_.hash_type() == SHA256:
            event.add_attribute("sha256", str(hash_))
        return event

    def handle_ipaddress(self, event: MISPEvent, ipaddress: IPAddress) -> MISPEvent:
        """Handle a single IP address."""
        event.add_attribute("ip-dst", str(ipaddress))
        return event

    def handle_url(self, event: MISPEvent, url: URL) -> MISPEvent:
        """Handle a single URL."""
        event.add_attribute("url", str(url))
        return event
