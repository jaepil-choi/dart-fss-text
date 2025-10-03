"""Integration tests for dart-fss-text.

Integration tests validate components with external dependencies:
- Live DART API calls
- Real MongoDB connections
- File system operations

Run with: poetry run pytest tests/integration/ -v -s
Skip in CI: pytest -m "not integration"
"""

