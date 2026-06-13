# Contributing to llm-prompt-compress

Thanks for your interest in contributing! This project provides heuristic prompt
compression for LLM context budgeting. It is intentionally small, dependency-free,
and targets Python 3.10+.

## Getting started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install the project in editable mode with the
   development extras:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

## Development workflow

1. Create a feature branch off `main`:

   ```bash
   git checkout -b my-feature
   ```

2. Make your change. Please keep the library zero-dependency at runtime — new
   third-party runtime dependencies are unlikely to be accepted.

3. Run the lint and test suite locally before opening a pull request. These are the
   same checks the CI workflow runs:

   ```bash
   ruff check src/ tests/
   pytest -v --tb=short
   ```

4. Add or update tests in `tests/` for any behavior change.

## Pull requests

- Keep pull requests focused and reasonably small.
- Make sure CI is green. The CI matrix runs against Python 3.10, 3.11, 3.12, and 3.13,
  so avoid syntax or APIs that are not available across that range.
- Write a clear description explaining the motivation and the change.
- Update the README or docstrings if you change public behavior.

## Code style

- Formatting and linting are enforced with [Ruff](https://docs.astral.sh/ruff/).
- Prefer small, well-named functions and clear, readable code over cleverness.
- Public functions should have concise docstrings.

## Reporting issues

When filing a bug report, please include:

- A short description of the expected vs. actual behavior.
- A minimal reproducible example, if possible.
- Your Python version and operating system.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
