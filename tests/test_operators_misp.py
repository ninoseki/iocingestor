import unittest
from unittest.mock import ANY as MOCK_ANY
from unittest.mock import patch

import iocingestor.artifacts
import iocingestor.operators.misp


class TestThreatKB(unittest.TestCase):
    @patch("pymisp.ExpandedPyMISP")
    def setUp(self, ExpandedPyMISP):
        self.misp = iocingestor.operators.misp.Plugin("a", "b")

    @patch("pymisp.ExpandedPyMISP")
    def test_tags_are_set_if_passed_in_else_default(self, ExpandedPyMISP):
        self.assertEqual(self.misp.tags, ["type:OSINT"])
        self.assertEqual(
            iocingestor.operators.misp.Plugin("a", "b", tags=["c", "d"]).tags,
            ["c", "d"],
        )

    def test_create_event_creates_event_and_objects(self):
        event = self.misp._create_event(
            iocingestor.artifacts.Domain(
                "test.com", "name", reference_link="link", reference_text="text"
            )
        )
        self.misp._update_or_create_event(event)
        self.misp.api.add_event.assert_called_once_with(event, pythonify=True)

    def test_handle_domain_creates_domain(self):
        domain = iocingestor.artifacts.Domain("test.com", "", "")

        event = self.misp._create_event(domain)
        event = self.misp.handle_domain(event, domain)
        self.assertEqual(event.Attribute[0].value, str(domain))

    def test_handle_hash_creates_hash(self):
        hash = iocingestor.artifacts.Hash("68b329da9893e34099c7d8ad5cb9c940", "", "")
        event = self.misp._create_event(hash)
        event = self.misp.handle_hash(event, hash)
        self.assertEqual(event.Attribute[0].value, str(hash))

        hash = iocingestor.artifacts.Hash(
            "adc83b19e793491b1c6ea0fd8b46cd9f32e592fc", "", ""
        )
        event = self.misp._create_event(hash)
        event = self.misp.handle_hash(event, hash)
        self.assertEqual(event.Attribute[0].value, str(hash))

        hash = iocingestor.artifacts.Hash(
            "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b", "", ""
        )
        event = self.misp._create_event(hash)
        event = self.misp.handle_hash(event, hash)
        self.assertEqual(event.Attribute[0].value, str(hash))

        hash = iocingestor.artifacts.Hash("invalid", "", "")
        event = self.misp._create_event(hash)
        event = self.misp.handle_hash(event, hash)
        self.assertEqual(event.Attribute, [])

    def test_handle_ipaddress_creates_ipaddress(self):
        ipaddress = iocingestor.artifacts.IPAddress("123.123.123.123", "", "")
        event = self.misp._create_event(ipaddress)
        event = self.misp.handle_ipaddress(event, ipaddress)
        self.assertEqual(event.Attribute[0].value, str(ipaddress))

    def test_handle_url_creates_url(self):
        url = iocingestor.artifacts.URL("http://example.com", "", "")
        event = self.misp._create_event(url)
        event = self.misp.handle_url(event, url)
        self.assertEqual(event.Attribute[0].value, str(url))

    def test_handle_artifact_creates_event(self):
        artifact = iocingestor.artifacts.URL("http://example.com", "", "")
        self.misp.handle_artifact(artifact)
        self.misp.api.add_event.assert_called_once()

    @patch("pymisp.ExpandedPyMISP")
    def test_artifact_types_are_set_if_passed_in_else_default(self, ExpandedPyMISP):
        artifact_types = [
            iocingestor.artifacts.IPAddress,
            iocingestor.artifacts.URL,
        ]
        self.assertEqual(
            iocingestor.operators.misp.Plugin(
                "a", "b", artifact_types=artifact_types
            ).artifact_types,
            artifact_types,
        )
        self.assertEqual(
            iocingestor.operators.misp.Plugin("a", "b").artifact_types,
            [
                iocingestor.artifacts.Domain,
                iocingestor.artifacts.Hash,
                iocingestor.artifacts.IPAddress,
                iocingestor.artifacts.URL,
            ],
        )

    @patch("pymisp.ExpandedPyMISP")
    def test_filter_string_and_allowed_sources_are_set_if_passed_in(
        self, ExpandedPyMISP
    ):
        self.assertEqual(
            iocingestor.operators.misp.Plugin(
                "a", "b", filter_string="test"
            ).filter_string,
            "test",
        )
        self.assertEqual(
            iocingestor.operators.misp.Plugin(
                "a", "b", allowed_sources=["test-one"]
            ).allowed_sources,
            ["test-one"],
        )

    @patch("pymisp.ExpandedPyMISP")
    def test_include_artifact_source_name(self, ExpandedPyMISP):
        self.assertFalse(
            iocingestor.operators.misp.Plugin(
                "a", "b", include_artifact_source_name=False
            ).include_artifact_source_name,
        )

        misp = iocingestor.operators.misp.Plugin(
            "a", "b", include_artifact_source_name=False
        )

        ipaddress = iocingestor.artifacts.IPAddress("123.123.123.123", "source", "")
        event = misp._create_event(ipaddress)
        event = misp.handle_ipaddress(event, ipaddress)
        attribute_types = [attribute.type for attribute in event.attributes]
        self.assertNotIn("other", attribute_types)
