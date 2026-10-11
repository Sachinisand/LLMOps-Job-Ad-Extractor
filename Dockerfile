FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY jobad_llmops/ jobad_llmops/
COPY prompts/ prompts/
COPY eval/ eval/
COPY config.yaml .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "jobad_llmops.api:app", "--host", "0.0.0.0", "--port", "8000"]
