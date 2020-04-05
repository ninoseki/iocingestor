import json
from pathlib import Path
from typing import List, Set


class Whitelist:
    """Base class for Whitelist plugin."""

    def __init__(self, paths: List[str]):
        self.paths = paths
        self.values: Set[str] = set()
        self._load_paths()

    def contains(self, value: str) -> bool:
        return value in self.values

    def _load_path(self, path: str):
        if Path(path).is_file():
            with open(path) as f:
                data = json.load(f)
                list_ = data.get("list", [])
                self.values.update(list_)

    def _load_paths(self):
        for path in self.paths:
            self._load_path(path)
