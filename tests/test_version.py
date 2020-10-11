import re

from iocingestor import __version__


def test_version():
    assert re.match("^[0-9]+\\.[0-9]+\\.[0-9]+$", __version__) is not None
