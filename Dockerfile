FROM python:3.11-slim

WORKDIR /app

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv
RUN /uv/bin/uv sync --frozen --no-cache

# Copy application source files
COPY . .

# Initialize SQLite database
RUN /uv/bin/uv run python init_db.py

EXPOSE 8000

CMD ["/uv/bin/uv", "run", "python", "server.py"]
