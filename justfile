default: sync lint format typecheck

sync:
    uv sync --all-groups

lint:
    uv run ruff check --fix .

format:
    uv run ruff format .

typecheck:
    uv run mypy --strict .

clean:
    - rm -r .mypy_cache .ruff_cache .venv
    find . -type d -name "__pycache__" -exec rm -r {} +
    
run:
    uv run python main.py

audit:
    uv run pip-audit

create-invite:
    uv run python cli.py -c tastie create-invite