FROM python:3.12-slim

WORKDIR /app

# Instalam uv
RUN pip install --no-cache-dir uv

# Copiem fisierele de dependinte
COPY pyproject.toml uv.lock ./

# Instalam dependintele
RUN uv sync --frozen --no-dev

# Copiem codul sursa al aplicatiei
COPY . .

# Expunem portul FastAPI
EXPOSE 8000

# Rulam aplicatia folosind uv (foloseste automat .venv)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
