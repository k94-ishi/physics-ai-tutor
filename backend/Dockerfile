FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* README.md ./

RUN uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "physics_ai_tutor.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]