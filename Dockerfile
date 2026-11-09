FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --create-home --uid 10001 appuser && chown appuser:appuser /app
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser data ./data
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=3)"
CMD ["sh", "-c", "exec uvicorn app.main:app --factory --host 0.0.0.0 --port ${PORT:-8000}"]

FROM runtime AS test
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser scripts ./scripts
CMD ["python", "scripts/run_tests.py"]

FROM runtime AS production
