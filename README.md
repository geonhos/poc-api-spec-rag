# poc-api-spec-rag

RAG-based API specification assistant that generates accurate cURL and request examples from OpenAPI documents.

## Installation

### Python

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### With Poetry (Recommended)

```bash
poetry install
poetry shell
```

## Usage

```bash
# Add usage instructions
python src/main.py
```

## Development

### Setup

1. Clone the repository
2. Create virtual environment and install dependencies
3. Configure `.env` file with required API keys:
   ```bash
   cp .env.example .env
   # Edit .env and add your tokens
   ```

### Testing

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy src/
```

## Project Structure

```
poc-api-spec-rag/
├── src/                   # Source code
├── tests/                 # Test files
├── docs/                  # Documentation
├── .venv/                 # Virtual environment
├── .claude/               # Claude Code settings
├── .mcp.json              # MCP server configuration
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment template
├── requirements.txt       # Dependencies
├── pyproject.toml         # Poetry configuration
└── README.md              # This file
```

## Important Notes

- **Tests run automatically before commits** (pre-commit hook)
- Follow TDD workflow: Red → Green → Refactor
- Use virtual environment for all development
- Never commit `.env` file (contains secrets)

## License

MIT
