# iocingestor

[![PyPI version](https://badge.fury.io/py/iocingestor.svg)](https://badge.fury.io/py/iocingestor)
[![Build Status](https://travis-ci.com/ninoseki/iocingestor.svg?branch=master)](https://travis-ci.com/ninoseki/iocingestor)
[![Coverage Status](https://coveralls.io/repos/github/ninoseki/iocingestor/badge.svg?branch=master)](https://coveralls.io/github/ninoseki/iocingestor?branch=master)
[![CodeFactor](https://www.codefactor.io/repository/github/ninoseki/iocingestor/badge)](https://www.codefactor.io/repository/github/ninoseki/iocingestor)

An extendable tool to extract and aggregate IoCs from threat feeds.

This tool is a forked version of [InQuest](https://inquest.net/)'s [ThreatIngestor](https://github.com/InQuest/ThreatIngestor) focuses on [MISP](https://www.misp-project.org/) integration.

## Key differences

- Better MISP integration.
  - Working with the latest version of MISP.
  - Smart event management based on `reference_link`.
- [MISP warninglist](https://github.com/MISP/misp-warninglists) compatible whitelisting.
- Using [ioc-finder](https://github.com/fhightower/ioc-finder) instead of [iocextract](https://github.com/InQuest/python-iocextract) for IoC extraction.
  - YARA rule extraction is dropped.

## Installation

iocingestor requires Python 3.6+.

Install iocingestor from PyPI:

```bash
pip install iocingestor
```

## Usage

Create a new `config.yml` file, and configure each source and operator module you want to use. (See `config.example.yml` as a reference.)

```bash
iocingestor config.yml
```

By default, it will run forever, polling each configured source every 15 minutes.

## Plugins

iocingestor uses a plugin architecture with "source" (input) and "operator" (output) plugins. The currently supported integrations are:

### Sources

- GitHub repository search
- RSS feeds
- Twitter
- Generic web pages

### Operators

- CSV files
- MISP
- SQLite database
