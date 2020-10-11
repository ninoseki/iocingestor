import collections
import json
import sys
import time
from typing import Dict, List, Type

import poetry_version
import statsd
from loguru import logger

from iocingestor import config, exceptions, state
from iocingestor.artifacts import Artifact
from iocingestor.whitelists import Whitelist

__version__ = str(poetry_version.extract(source_file=__file__))


class Ingestor:
    """iocingestor main work logic.

    Handles reading the config file, calling sources, maintaining state, and
    sending artifacts to operators.
    """

    def __init__(self, config_file: str):
        # Load config.
        try:
            logger.debug(f"Reading config from '{config_file}'")
            self.config = config.Config(config_file)
        except (OSError, exceptions.IngestorError):
            # Error loading config.
            logger.exception("Couldn't read config")
            sys.exit(1)

        # Configure logging with optional notifiers.
        logger.configure(**self.config.logging())
        try:
            logger.level("NOTIFY", no=35, color="<yellow>", icon="\U0001F514")
        except TypeError:
            # logger raises TypeError if NOTIFY is already defined
            pass

        logger.debug("Log handler reconfigured")

        # Configure statsd.
        try:
            self.statsd = statsd.StatsClient(**self.config.statsd())
            self.statsd.incr("start")
        except TypeError:
            logger.exception("Couldn't initialize statsd client; bad config?")
            sys.exit(1)

        # Load state DB.
        try:
            logger.debug(f"Opening state database '{self.config.state_path()}'")
            self.statedb = state.State(self.config.state_path())
        except (OSError, exceptions.IngestorError):
            # Error loading state DB.
            logger.exception("Error reading state database")
            sys.exit(1)

        # Instantiate plugins.
        try:
            logger.debug("Initializing sources")
            self.sources = {
                name: source(**kwargs) for name, source, kwargs in self.config.sources()
            }

            logger.debug("Initializing operators")
            self.operators = {
                name: operator(**kwargs)
                for name, operator, kwargs in self.config.operators()
            }

        except (TypeError, ConnectionError, exceptions.PluginError):
            logger.exception("Error initializing plugins")
            sys.exit(1)

        # Load whitelists
        try:
            logger.debug("Load whitelists")
            self.whitelist = Whitelist(self.config.whitelists())
        except json.decoder.JSONDecodeError:
            logger.exception("Error loading whitelists")
            sys.exit(1)

    def _contains_in_whitelist(self, artifact: Type[Artifact]) -> bool:
        if self.whitelist.contains(str(artifact)):
            logger.debug(
                f"Reject {str(artifact)} from further processing because it is whitelisetd"
            )
            return True
        return False

    def run(self):
        """Run once, or forever, depending on config."""
        if self.config.daemon():
            logger.debug("Running forever, in a loop")
            self.run_forever()
        else:
            logger.debug("Running once, to completion")
            with self.statsd.timer("run_once"):
                self.run_once()

    def run_once(self):
        """Run each source once, passing artifacts to each operator."""
        # Track some statistics about artifacts in a summary object.
        summary = collections.Counter()

        for source in self.sources:
            # Run the source to collect artifacts.
            logger.debug(f"Running source '{source}'")
            try:
                with self.statsd.timer(f"source.{source}"):
                    saved_state, artifacts = self.sources[source].run(
                        self.statedb.get_state(source)
                    )

            except Exception:
                self.statsd.incr(f"error.source.{source}")
                logger.exception(f"Unknown error in source '{source}'")
                continue

            # Save the source state.
            self.statedb.save_state(source, saved_state)

            # Reject whitelisted artifacts
            artifacts = [
                artifact
                for artifact in artifacts
                if not self._contains_in_whitelist(artifact)
            ]

            # Process artifacts with each operator.
            for operator in self.operators:
                logger.debug(
                    f"Processing {len(artifacts)} artifacts from source '{source}' with operator '{operator}'"
                )
                try:
                    with self.statsd.timer(f"operator.{operator}"):
                        self.operators[operator].process(artifacts)

                except Exception:
                    self.statsd.incr(f"error.operator.{operator}")
                    logger.exception(f"Unknown error in operator '{operator}'")
                    continue

            # Record stats and update the summary.
            types = artifact_types(artifacts)
            summary.update(types)
            for artifact_type in types:
                self.statsd.incr(
                    f"source.{source}.{artifact_type}", types[artifact_type]
                )
                self.statsd.incr(f"artifacts.{artifact_type}", types[artifact_type])

        # Log the summary.
        logger.log("NOTIFY", f"New artifacts: {dict(summary)}")

    def run_forever(self):
        """Run forever, sleeping for the configured interval between each run."""
        while True:
            with self.statsd.timer("run_once"):
                self.run_once()

            logger.debug(f"Sleeping for {self.config.sleep()} seconds")
            time.sleep(self.config.sleep())


def artifact_types(artifact_list: List[Artifact]) -> Dict[str, int]:
    """Return a dictionary with counts of each artifact type."""
    types: Dict[str, int] = {}
    for artifact in artifact_list:
        artifact_type: str = artifact.__class__.__name__.lower()
        if artifact_type in types:
            types[artifact_type] += 1
        else:
            types[artifact_type] = 1

    return types


def main():
    """CLI entry point, uses sys.argv directly."""
    if len(sys.argv) < 2:
        logger.error("You must specify a config file")
        sys.exit(1)

    app = Ingestor(sys.argv[1])
    app.run()


if __name__ == "__main__":
    main()
