FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --quiet

COPY pyproject.toml .
RUN uv pip install --system .

COPY . .

VOLUME ["/data"]

CMD ["python", "main.py"]
