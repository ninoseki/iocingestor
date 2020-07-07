#!/usr/bin/env python
"""Fang indicators of compromise."""
import json
import os
import re

try:
    from iocingestor.ioc_fanger import grammars as grammars
except AttributeError:
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
    import grammars


FANG_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "./fang.json"))


def _get_data_from_file(file_path):
    """Get data from the given file path."""
    with open(file_path) as f:
        return json.loads(f.read())


# get the mappings to fang indicators of compromise
fanging_mappings = _get_data_from_file(FANG_DATA_PATH)


def fang(text, debug=False):
    """Fang the indicators in the given text."""
    fanged_text = text

    if debug:
        print(f"Starting text: {fanged_text}")
        print("-----")

    fanged_text = grammars.dot_fanging_patterns.transformString(fanged_text)
    fanged_text = grammars.at_fanging_patterns.transformString(fanged_text)
    fanged_text = grammars.more_at_fanging_patterns.transformString(fanged_text)
    fanged_text = grammars.colon_slash_slash_fanging_patterns.transformString(
        fanged_text
    )
    fanged_text = grammars.colon_fanging_patterns.transformString(fanged_text)
    fanged_text = grammars.odd_url_scheme_form.transformString(fanged_text)
    fanged_text = grammars.http_fanging_patterns.transformString(fanged_text)
    fanged_text = grammars.comma_fanging_patterns.transformString(fanged_text)

    for mapping in fanging_mappings:
        if debug:
            print(f"Mapping: {mapping}")

        if mapping.get("regex"):
            find_value = mapping["find"]
        else:
            find_value = re.escape(mapping["find"])

        if mapping.get("case_sensitive"):
            fanged_text = re.sub(find_value, mapping["replace"], fanged_text)
        else:
            fanged_text = re.sub(
                find_value, mapping["replace"], fanged_text, flags=re.IGNORECASE
            )

        if debug:
            print(f"Text after mapping: {fanged_text}")
            print("-----")

    return fanged_text
