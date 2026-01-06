# grillgauge

A CLI tool for grillgauge

## Installation

This package uses Poetry for dependency management. To install:

1. Ensure you have Poetry installed: `curl -sSL https://install.python-poetry.org | python3 -`
2. Clone or download the project.
3. Run `poetry install` to install dependencies.

## Setup

### Environment Variables

Create a `.env` file in the project root with your configurations.

## Usage

```bash
poetry run python -m grillgauge.generator --help
```

## Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=grillgauge
```