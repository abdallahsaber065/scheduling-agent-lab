FROM python:3.11-slim

WORKDIR /app

# Install uv binary via official installer script
RUN apt-get update && apt-get install -y curl && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv
RUN /root/.local/bin/uv sync --frozen --no-cache

# Copy application source files
COPY . .

# Initialize SQLite database
RUN /root/.local/bin/uv run python init_db.py

EXPOSE 8000

CMD ["/root/.local/bin/uv", "run", "python", "server.py"]
