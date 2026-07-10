# Dockerfile del backend SICOP-MDSJ.
#
# Runtime: Python 3.12 + ODBC Driver 17 for SQL Server (para SIGA)
# + WeasyPrint (Cairo/Pango/GDK) para exportación PDF (T-30).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ─── ODBC Driver 17 for SQL Server ────────────────────────────────────────
# Requerido por pyodbc para conectarse a SIGA.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg apt-transport-https ca-certificates \
        # Dependencias runtime de WeasyPrint (PDF)
        libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
        libffi-dev shared-mime-info fonts-dejavu \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql17 unixodbc \
    && rm -rf /var/lib/apt/lists/*

# ─── Instalación de dependencias Python ──────────────────────────────────
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install .

# ─── Código de la app ────────────────────────────────────────────────────
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

EXPOSE 8000

# Health check interno del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
