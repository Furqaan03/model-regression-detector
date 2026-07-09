FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--prompt-version", "v1", "--fail-on-critical"]
