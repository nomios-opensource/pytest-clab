# Contributing to pytest-clab

All contributions are welcome - bug reports, feature requests, documentation improvements, and code changes.

## Getting Started

1. Fork and clone the repository
2. Install dependencies with [uv](https://docs.astral.sh/uv/):

   ```bash
   uv sync
   ```

3. Create a branch for your changes:

   ```bash
   git checkout -b my-feature
   ```

## Development

Install the pre-commit hooks so formatting, linting, type checking, and unit tests run automatically on each commit:

```bash
pre-commit install
```

This runs ruff, mypy, and the unit test suite before every commit. If you need to run checks manually:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy pytest_clab
```

E2E tests require [containerlab](https://containerlab.dev/) installed:

```bash
uv run pytest -m e2e
```

## Code Style

- Formatting and linting are handled by [ruff](https://docs.astral.sh/ruff/)
- Type annotations are checked with [mypy](https://mypy-lang.org/)
- Tests follow Given-When-Then naming: `test_given_X_when_Y_then_Z`

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated releases. Prefix your commit messages with a type:

- `feat:` new feature (triggers a minor version bump)
- `fix:` bug fix (triggers a patch version bump)
- `docs:` documentation only
- `test:` adding or updating tests
- `ci:` CI/CD changes
- `refactor:` code changes that neither fix a bug nor add a feature

Example: `feat: add support for custom node labels`

## Submitting Changes

1. Keep pull requests focused on a single change
2. Include tests for new functionality or bug fixes
3. Ensure all checks pass before requesting review

## Reporting Bugs & Requesting Features

Open an issue on [GitHub Issues](https://github.com/nomios-open-source/pytest-clab/issues). For bugs, include steps to reproduce, expected behavior, and actual behavior.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.